import os, copy, ConfigParser

class Config:

    default_values = {
        'config': ['/etc/downpour.cfg',
            os.path.expanduser('~/.config/downpour/downpour.cfg')],
        'downpour': {
            'state': os.path.expanduser('~/.config/downpour/downpour.db'),
            'log': 'info',
            'interface': '0.0.0.0',
            'plugins': 'downpour2.web.WebInterfacePlugin'
        },
        'downpour2.web.WebInterfacePlugin': {
            'port': 6280
        }
    }

    def __init__(self, options=None):

        self.values = copy.deepcopy(Config.default_values)

        # Load configuration from file
        config = self.values['config']
        if options and options.has_key('config'):
            config.append(os.path.expanduser(options['config']))
        self.values['config'] = config
        cfgparser = ConfigParser.RawConfigParser()
        cfgparser.read(config)
        for section in cfgparser.sections():
            if not self.values.has_key(section):
                self.values[section] = {}
            for pair in cfgparser.items(section):
                self.values[section][pair[0]] = pair[1]

        # Override a limited set of options from command line
        if options:
            sections = {
                'log': self.values['downpour'],
                'interface': self.values['downpour'],
                'port': self.values['downpour2.web.WebInterfacePlugin']
            }
            for key in options:
                if options[key] is not None and sections.has_key(key):
                    sections[key][key] = options[key]

    def section(self, section):
        if section in self.values:
            return self.values[section]
        return {}

    def value(self, option, default=None):
        if option[0] in self.values and option[1] in self.values[option[0]]:
            return self.values[option[0]][option[1]]
        return default
