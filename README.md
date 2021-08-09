# Generation of IEC 60601-1-8 Conform Sounds

### Overview

This folder contains the scripts and configuration files to create
IEC60601-1-8 conform sound files. The example configuration files:

- example_HP_config.py:   generates high priority alarms:
			  A high priority alarm has 3 equidistant pulses
			  followed by 2 equidistant pulses. These 5 pulses
			  repeat after a silence. 
- example_LP_config.py:   generates low priority alarms:
			  A low priority alarm has ONE or TWO pulses 

are in valid Python syntax.

Alternatively you can run each script without configuration files or with
configuration files and modify single parameters.

The script will ask you all configuration parameters and you can
accept the defaults. If you change parameters, any possible input is allowed.
You will receive a warning if a parameter would lead to a non-IEC60601-1-8
conform sound.

All aspects of IEC60601-1-8 will be checked. However, there is no guarantee,
that the generated sounds will automatically be IEC60601-1-8
conform once they are produced by the target device hardware because of
device resonance, amplifying deviations, speaker performance etc.


### Important Note

When using the sound generation scripts, please DO READ all information
provided and read the query in full and provide a valid setting!!!


### Scripts

high_prio_sound_gen.py:
	Script to generate high priority alarms.
low_prio_sound_gen.py:
	Script to generate low priority alarms.
wavtools.py:
	common functionality used by high_prio_sound_gen.py and
	low_prio_sound_gen.py 
	

### Usage

For generation of high priority alarms call
```
    ./high_prio_sound_gen.py example_HP_config.py
```
    which uses the configuration example_HP_config.py
    for default settings (i.e. if you accept all settings by pressing
    enter).

    The script querries all parameters and will warn you if a parameter
    will create a non-IEC60601-1-8 compliant sound file.

    The (new) parametrization is written to hp_alarm.py and the sound file
    is written to new-hp.wav (these output filenames can be changed
    in the script).

For generation of low priority alarms call
```
    ./low_prio_sound_gen.py example_LP_config.py
```
    which uses the configuration example_LP_config.py
    for default settings (i.e. if you accept all settings by pressing
    enter).

    The script querries all parameters and will warn you if a parameter
    will create a non-IEC60601-1-8 compliant sound file.

    The (new) parametrization is written to lp_alarm.py and the sound file
    is written to new-lp.wav (these output filenames can be changed
    in the script).
