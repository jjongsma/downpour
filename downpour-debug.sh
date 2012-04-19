#/bin/bash
# Quick way to launch downpour in debug mode if you
# are developing features for it in the src/ directory

if test ! -e "debug"; then
	mkdir debug
	mkdir debug/user-dir
	mkdir debug/work-dir
fi
DOWNPOUR_DEBUG=1 bin/downpourd -c cfg/debug.cfg -d
