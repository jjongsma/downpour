import sys, os, time, atexit, pwd, grp
from signal import SIGTERM 

class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, launcher, pidfile=None, user=None, group=None, umask=077, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.launcher = launcher
        self.pidfile = pidfile
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.user = user
        self.group = group
        self.umask = umask
        self.args = []
        self.kwargs = {}
    
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        
        if not os.access(os.path.dirname(self.pidfile), os.W_OK):
            sys.stderr.write("No write access to pidfile: %s\n" % self.pidfile)
            sys.exit(1)

        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
        
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
        if self.user:
            os.chown(self.pidfile, pwd.getpwnam(self.user)[2], grp.getgrnam(self.group)[2])
    
    def drop_privileges(self):
        if self.user and os.getuid() == 0:
            try:
                os.setgid(grp.getgrnam(self.group)[2])
                os.setuid(pwd.getpwnam(self.user)[2])
            except OSError as e:
                sys.stderr.write('Could not set user or group: %s' % e)
                sys.exit(1) 
            old_umask = os.umask(self.umask)

    def delpid(self):
        if (os.path.exists(self.pidfile)):
            try:
                os.remove(self.pidfile)
            except OSError:
                pass

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if pid:
            try:
                os.kill(pid, 0)
                message = "pidfile %s already exist. Daemon already running?\n"
                sys.stderr.write(message % self.pidfile)
                sys.exit(1)
            except OSError:
                pass
        
        # Start the daemon
        self.daemonize()
        self.drop_privileges()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        launch_class = self.get_class(self.launcher)
        launch_class(*self.args, **self.kwargs).run(self.pidfile)

    def get_class(self, kls):
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)            
        return m
