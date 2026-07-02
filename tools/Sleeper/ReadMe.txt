PassMark (R) Software's Sleeper
Copyright (C) 2006-2016 PassMark Software
All Rights Reserved
http://www.passmark.com

Overview
========
Sleeper is a small utility program developed by PassMark Software to help
test the ability of PC systems to enter and recover from sleep and hibernation


Status
======
Sleeper is free for personal use and free for customers that have purchased BurnInTest.


Installation
============
There is no installation required. Unzip the zip file and run the Sleeper.exe file.


UnInstallation
==============
Delete the folder that it was previously installed in or delete
the contents of the folder.
	

Requirements
======================
Platforms: XP, 2003, Vista, Windows 7, Windows 8, Windows 10
Requirements: 32MB Ram
Must be run as administrator


Version History
===============
Here is a summary of all changes that have been made in each version of Sleeper.

Revision			Author		Date

Sleeper v2.3 (1010)		MB		30 Mar 2016
-------------------------------------------------------------------
1.	Fixed a bug where Sleeper was crashing on automatic exit

Sleeper v2.3 (1009)		TR		15 Oct 2012
-------------------------------------------------------------------
1.	Fixed a bug where the cycle count was not being logged correctly

Sleeper v2.3 (1008)		TR		10 Oct 2012
-------------------------------------------------------------------
1.	Fixed a bug that could prevent the "sleep time too short" error being displayed correctly
2.	Updated the help to add some information about warning and error conditions

Sleeper v2.3 (1007)		TR		13 Sept 2012
-------------------------------------------------------------------
1.	Fixed a registry write error in Windows 8 when using the "Restart automatically after power cycle" option
			
Sleeper v2.3 (1006)		MF		12 May 2010
-------------------------------------------------------------------
1.	Removed restriction prohibiting the running of external apps when using command line parameters
2.	Fixed bug where it was not possible to run when only hibernate mode is supported

Sleeper v2.3 (1005)		TR		22 May 2009
-------------------------------------------------------------------
1.	Added "Wake Source" log message when using "Debug & Events" configuration option (Vista Only)
2.	Fixed some possible crashes that could occur during logging

Sleeper v2.3 (1004)		MF		8 July 2008
-------------------------------------------------------------------
1.	Added additional error reporting for logging failures.

Sleeper v2.3 (1003)		MF		24 Sept 2007
-------------------------------------------------------------------
1.	Fixed a bug which only became apparent after Sleeper had been cycling for many hours.

Sleeper v2.3 (1002)		MF		10 July 2007
-------------------------------------------------------------------
1.	Added extra display box showing current cycle number.
2. 	Fixed a rare bug involving crashing on exit. 


Sleeper v2.3 (1001)		MF		4 July 2007
-------------------------------------------------------------------
1.	Help file updated for Vista.
2.	Sleeper now automatically requests to run as admin when using Vista.
3.	Tested to work with Vista.


Sleeper v2.3 (1000)		DW		5 Oct 2006
-------------------------------------------------------------------
1.	First attempt a being Vista compatible.
	In Vista may need to set administrator privilege level from .exe properties.
	More work, including a complete re-write of the help file is still required
	for full Vista compatibility.
2.	Additional checking and warnings messages about needing to be the administrator
3.	New icon with 256 colors
4.	Changes to a number of internal functions to give the software a better chance
	of working on Vista.


Sleeper v2.2 (1006)		SK		22 Dec 2005
-------------------------------------------------------------------
1.	Fixed bug whereby if the log file name length is too long, Sleeper's stack gets corrupt,
	resulting in unexpected behavior.  Log file name length can now accomodate up to 511 characters.
	If a -L option is followed by a log file name whose length is greater than 511, an error message box
	will be displayed.
2.	Fixed bug whereby log entry is written to the desktop.
3.	Added separators after coomand line options report.
4.	Added separators before "About to start next cycle"
5.	Fixed bug whereby -B does not override configuration file in command line, i.e.:
	Sleeper.exe --config=configAllSleepState.dat -B -E
	will execute all sleep states instead of only supported states.
6.	Feature enhancement: Sleeeper will create the log path if it does not exist.
	Supported paths are:
		a)	Absolute local path, i.e. beginning with an alphabet followed by a colon or
			beginning with an alpha-numeric and not followed by a colon.
			(Example:	A:\a\b\c\d\test.log, b:\1\2\3\4\5\here.log, etc,
					my\path\test.log, 1\2\3\test.log, etc)
		b)	Network path, i.e. beginning with double backslashes followed by the shared folder's name
			(Example:	\\userXP\sharedFolder\example.log, etc)
	Unsupported paths are:
		a)	Relative paths (i.e. paths that starts with dots or double dots, or paths
			that contains dots or double dots between back slashes)
			(Example:	.\my\path\test.log, ..\my\path\test.log, C:\a\b\..\c\.\my.log)
7.	Feature enhancement:	Sleeper will not support Hibernate (S4) if Hibernate is not enabled
	from Control Panel:Power Options.  It will treat it as an unsupported mode.  However, Sleeper
	does not prevent user from checking S4 and forcing system to Hibernate even though Hibernate is
	not enabled from the Control Panel:Power Options.


Sleeper v2.2 (1005)		SK		09 Dec 2005
-------------------------------------------------------------------
1.	Fix bug in configuration window whereby "Log to file", "Restart automatically after power cycle""
	and "Stop and prompt user upon error" cannot be unchecked once it is checked.
2.	Because "Log level:Debug" turns on trace logging in Sleeper's user visible log file, "debug.log"
	has been removed.
3.	Fix bug whereby "Log colour classification" is not repainted if sleep is skipped.
4.	Fixed bug whereby logs are split between 2 files.
5.	Fixed bug where invalid command line option causes crash.
6.	Added error dialog for invalid command line.
7.	Check boxes to run suspend states are now saved in configuration file.
8.	Change command line behavior to following:
	i)	If no command line options are specified, Sleeper will attempt to load the last
		used configuration (sleeperCfg.dat).  If sleeperCfg.dat is not present,
		default values will be used.
	ii)	If a configuration file is specified, the configuration file will be used.
	iii)	If a configuration file is specified along with other command line options,
		the configuration file will be used.  Any command line option that appears
		after the configuration file (i.e. --config option) will override the
		configuration file's settings.  For example, if the sleep duration for S1-S4
		is 60 in "myconfig.dat", and we run Sleeper with:
		Sleeper.exe --config=myconfig.dat -R 90.
		Then Sleeper will attempt to sleep for 90 seconds instead of 60
	iv)	If command line options are specified without a configuration file
		(i.e. without --config option), default values will be used and the
		command line options will override its default values.  If any of the
		command line option is invalid, Sleeper will use its default values.
		However, if a valid log file is specified (i.e. valid -L, -La or -Lo option)
		along with other invalid options, logs will be written to the specified log file
9.	Added -La (append to log) and -Lo (overwrite log) in command line.
10.	Sets default behavior to append to log unless -Lo is specified.
11.	Changed behavior where if log file name is changed in Configuration window, it will only
	take effect from next start of Sleeper.



Sleeper v2.2 (1004)		SK		02 Dec 2005
-------------------------------------------------------------------
1.	Added Log colour classification in main window.
2.	Some bug fixes.

Sleeper v2.2 (1003)		SK		30 Nov 2005
-------------------------------------------------------------------
1.	Created Readme.txt for Sleeper.
2.	Added Sleeper version (and built date/time) to log file.
3.	Added ability to specifiy duration per sleep state from command line.
4.	Added logging of sleep states that are not supported.
5.	Added 4 radio buttons in config window that specify the state fallback (when a requested state
	is not supported).  Also add this cbility from command line.
6.	Added command line option -O or -O[x] that queries (without executing any sleep states) which
	sleep states are supported.
7.	Added ability to load and save config by adding a "Load Config" and "Save Config" button in config dialog.
	Also added this ability from command line with syntax --config==config_file.dat
8.	Added ability to have debug(trace) logging in user visible log file.
9.	Added 3 radio buttons in config window that user can choose level of logging.
10.	Updated SLEEPER.HLP with above changes.


Documentation
=============
All the documentation is included in the online help file.
It can be accessed from the help button.


Support
=======
For technical support, questions, suggestions, please check the help file for 
our email address or visit our web page at http://www.passmark.com/support/index.htm


Ordering / Registration
=======================
All the details are in the help file documentation
or you can visit our sales information page
http://www.passmark.com/sales



Enjoy..
The PassMark Development team
