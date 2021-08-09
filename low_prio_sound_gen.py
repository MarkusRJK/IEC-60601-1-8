#!/usr/bin/python 

from __future__ import division
from wavtools import getVolumes
from wavtools import volumesOutOfDbRange
from wavtools import hasEnoughHarmonics
from wavtools import hasSignificantVolumesInsideDbRange
from wavtools import getMax
from wavtools import save_wav
from wavtools import IEC_60601_1_8_Pulse
from wavtools import PulseMerger
from wavtools import introduction
from wavtools import maxDiffSoundPressureToPulseFrequencyInDB
from shutil   import copyfile
import subprocess
import os
import sys

# specify, where you want to save the file and its filename:
#outputFilePath = os.environ['HOME'] + "/Downloads/sounds/low-prio-new.wav"
outputFilePath = "new-lp.wav"
# name where a new configuration is saved:
# IMPORTANT NOTE: name must be the same as in the (next) import statement
#                 below around line 122
lpConfigFilename = 'lp_alarm'
# if you want to also remote copy it to a device via scp, specify
# the remote target here in the form of a scp target, e.g.
# someuser@host:path. See scp for more details. If you set
# the remote to None, no attempt for scp is made.
remoteSCPtarget = None


# NOTE: you will see several sections of settings the later overwriting the
#       priors. This is intented so you can see the history where it began.


###############################################################################
# Default Settings 
###############################################################################
# See IEC_60601_1_8_*_Pulse class for spacing, duration, rise and fall ranges
#
# NOTE: there were scripts to generate 8kHz and 44.1kHz bursts
defaultSampleRate_Hz = 44100
# NOTE: pulse spacing in initial script did not cover from 90% of the fall
#       mark to 90% of the rise mark
defaultPulseSpacing_ms = 180
# NOTE: pulse duration in initial script did not cover from 90% of the rise
#       mark to 90% of the fall mark
defaultPulseDuration_ms = 180
# NOTE: default rise and fall time were measured from the output and was
#       actually around 8.8
defaultRiseTime_pc = 20
defaultFallTime_pc = 10
defaultBaseFrequency1 = 505 
defaultHarmonicStr1 = "1 3 5 7 9"
defaultVolumeStr1 = "0.75 0.7 0.5 0.3 0.3"
defaultBaseFrequency2 = 400
defaultHarmonicStr2 = defaultHarmonicStr1
defaultVolumeStr2 = defaultVolumeStr1
# spacing between two bursts
defaultBurstSpacing_ms = 25000
# NOTE: the intial script output 5 wave files that had to be merged with an
#       external tool e.g. audacity. Audacity caused clippings whatever way
#       it merged the files.
# gain in (0.0; 1.0]
gain = 0.98

###############################################################################
# Some devices may require a small silence period at the start of a HP alarm
# default should be 0
###############################################################################

defaultStartWithSilence_ms = 0

###############################################################################
###############################################################################
###############################################################################

if len(sys.argv) > 1:
    copyfile(sys.argv[1], 'lp_alarm.py')
# NOTE: this import must come after all initialization
#       By the way Python is made lp_alarm must be located in the directory in
#       which THIS script (low_prio_sound_gen.py) resides.
try:
    from lp_alarm import defaultSampleRate_Hz
    from lp_alarm import defaultPulseSpacing_ms
    from lp_alarm import defaultPulseDuration_ms
    from lp_alarm import defaultRiseTime_pc
    from lp_alarm import defaultFallTime_pc
    from lp_alarm import defaultBaseFrequency1
    from lp_alarm import defaultHarmonicStr1
    from lp_alarm import defaultVolumeStr1
    from lp_alarm import defaultBaseFrequency2
    from lp_alarm import defaultHarmonicStr2
    from lp_alarm import defaultVolumeStr2
    from lp_alarm import defaultBurstSpacing_ms
    from lp_alarm import defaultStartWithSilence_ms
except:
    print("No config " + lpConfigFilename + ".py found\n")
    pass


def LP_introduction():
    print "Terminology - Low Priority Alarm:"
    print
    print "                        | burst spacing  |"
    print "   |------- burst -------|               |"
    print "   | |pulse|pulse|pulse| |               |"
    print "   | | ___ |space| ___ | |               |  __..."
    print "   | |/   \       /   \| |               | /"
    print "   | /     \     /     \ |               |/"
    print " __|/freq. 1\___/freq. 2\|_______________/"
    print ""
    print "Please set the maximum sound pressure difference to the fundamental"
    print "frequency of (at least 4) harmonics in wavtools.py."


# pulses may have different tones within this range:
baseFrequency_Hz_min = 150
baseFrequency_Hz_max = 1000

class IEC_60601_1_8_Low_Priority_Pulse(IEC_60601_1_8_Pulse):
    """
    Inherits from IEC_60601_1_8_Pulse and sets pulseDuration_ms_min|max
    and pulse_90pc_spacing_ms_min|max for Low Priority alarms.
    """
    # pulses spacing t_s (measured from 90% of the fall to 90% of the rise)
    pulse_90pc_spacing_ms_min=125
    pulse_90pc_spacing_ms_max=250
    _pulse_90pc_spacing_ms = None

    # low priority alarm pulse duration (t_d): 125ms to 250ms
    pulseDuration_ms_min=125
    pulseDuration_ms_max=250
    
    burstSpacing_ms_min=15000

    def setBurstSpacing_ms(self, bs = None):
        """
        spacing between two bursts in milliseconds (measured from 90% mark of the rise
        to 90% mark of the fall)
        """
        if bs is None:
            self._burstSpacing_ms = self.burstSpacing_ms_min
        else:
            self._burstSpacing_ms = max(0, bs)
        return self._burstSpacing_ms

    def getBurstSpacing_ms(self):
        return self._burstSpacing_ms

    def isBurstSpacingInRange(self):
        return self._burstSpacing_ms >= self.burstSpacing_ms_min

###############################################################################
###############################################################################
###############################################################################

print
introduction()
print
LP_introduction()
print
print

sampleRate_Hz = defaultSampleRate_Hz
try:
    select = input("Sample rate\n  0) 8kHz\n  1) 9.6kHz\n  2) 12kHz\n  3) 16kHz\n  4) 19.2kHz\n  5) 24kHz\n  6) 32kHz\n  7) 44.1kHz\n  8) 48kHz\n  9) 96kHz\nSelect [0; 9] (default: " + str(defaultSampleRate_Hz) + "): ")
    if select == 0:
        sampleRate_Hz = 8000
    if select == 1:
        sampleRate_Hz = 9600
    if select == 2:
        sampleRate_Hz = 12000
    if select == 3:
        sampleRate_Hz = 16000
    if select == 4:
        sampleRate_Hz = 19200
    if select == 5:
        sampleRate_Hz = 24000
    if select == 6:
        sampleRate_Hz = 32000
    if select == 7:
        sampleRate_Hz = 44100
    if select == 8:
        sampleRate_Hz = 48000
    if select == 9:
        sampleRate_Hz = 96000
except:
    pass
        
print("==> Selected sample rate: " + str(sampleRate_Hz) + " Hz\n")

pulse = IEC_60601_1_8_Low_Priority_Pulse()
pulse.setSampleRate_Hz(sampleRate_Hz)

###############################################################################

try:
    pulseSpacing_ms = input("Pulse spacing [" + str(pulse.pulse_90pc_spacing_ms_min) +  "ms; " + str(pulse.pulse_90pc_spacing_ms_max) + "ms] (default: " + str(defaultPulseSpacing_ms) + "ms): ")
except:
    pulseSpacing_ms = defaultPulseSpacing_ms

print("==> Selected pulse spacing: " + str(pulse.setPulseSpacing_ms(pulseSpacing_ms)) + " ms")
if (not pulse.isPulseSpacingInRange()):
    print("*** WARNING: pulse spacing out of range")
print

###############################################################################

try:
    pulseDuration_ms = input("Pulse duration [" + str(pulse.pulseDuration_ms_min) +  "ms; " + str(pulse.pulseDuration_ms_max) + "ms] (default: " + str(defaultPulseDuration_ms) + "ms): ")
except:
    pulseDuration_ms = defaultPulseDuration_ms

print("==> Selected pulse duration: " + str(pulse.setPulseDuration_ms(pulseDuration_ms)) + " ms")
if (not pulse.isPulseDurationInRange()):
    print("*** WARNING: pulse duration out of range")
print
 
###############################################################################

try:
    riseTime_pc = input("Rise time [" + str(pulse.riseTime_pc_min) +  "%; " + str(pulse.riseTime_pc_max) + "%] (default: " + str(defaultRiseTime_pc) + "%): ")
except:
    riseTime_pc = defaultRiseTime_pc  # 100 * (11 / 125) = 8.8% measures with Audaciy

print("==> Selected rise time: " + str(pulse.setRiseTime_pc(riseTime_pc)) + " %")
if (not pulse.isRiseTimeInRange()):
    print("*** WARNING: rise time out of range")
print

###############################################################################

try:
    fallTime_pc = input("Fall time [0%; 100%] (default: " + str(defaultFallTime_pc) + "%): ")
except:
    fallTime_pc = defaultFallTime_pc

print("==> Selected fall time: " + str(pulse.setFallTime_pc(fallTime_pc)) + " %")
if (not pulse.isFallTimeInRange()):
    print("*** WARNING: fall time out of range")
print

###############################################################################

try:
    baseFrequency1 = input("Base frequency of 1st pulse [" + str(baseFrequency_Hz_min) + "Hz; " + str(baseFrequency_Hz_max) + "Hz] (default: " + str(defaultBaseFrequency1) + "Hz): ")
except:
    baseFrequency1 = defaultBaseFrequency1 
  
print("==> Selected base frequency of 1st pulse: " + str(baseFrequency1))
# IEC 60601-1-8 page 17 requires base frequency in range [150Hz, 1000Hz]
if (baseFrequency_Hz_min > baseFrequency1 or baseFrequency1 > baseFrequency_Hz_max):
    print("*** WARNING: pulse frequency f_0 out of range")
print

# to keep this code simple we leave this task to the user: first harmonic is 1 and harmonics
# are sorted ascending.
print("IMPORTANT NOTE: the first harmonic must be 1 and the harmonics must be in ascending order!!!")
harmonicsStr1 = raw_input("Harmonics [positive integer] (default: " + defaultHarmonicStr1 + "): ")
if len(harmonicsStr1) == 0:
    harmonicsStr1 = defaultHarmonicStr1
 
print("==> Selected harmonics of 1st pulse: " + harmonicsStr1)
   
harmonics1 = harmonicsStr1.split()
noHarmonics = len(harmonics1)

# hasEnoughHarmonics ensures the correct format of harmonics. Hence call before
# working on harmonics
if (not hasEnoughHarmonics(baseFrequency1, harmonics1)):
    print("*** WARNING: less than required number of harmonics in range [300Hz, 4000Hz]")
print

###############################################################################

volumes1 = []
while len(volumes1) != noHarmonics:
    volumesStr1 = raw_input(str(noHarmonics) + " Volumes (default: " + defaultVolumeStr1 + "): ")
    if len(volumesStr1) == 0:
        volumesStr1 = defaultVolumeStr1
    volumes1 = getVolumes(volumesStr1)

print("==> Selected volumes of 1st pulse: " + volumesStr1)

dBvalue=str(maxDiffSoundPressureToPulseFrequencyInDB)
if (not hasSignificantVolumesInsideDbRange(volumes1, baseFrequency1, harmonics1)):
    print("*** WARNING: less than 4 harmonics with volumes +-" + dBvalue + "dB from base frequency's volume")
    print("            "),
    vOODbR = volumesOutOfDbRange(volumes1)
    print("             The following volumes differ more than " + dBvalue + "dB from base frequency's volume:")
    for v in vOODbR:
        print(str(v) + ", "),
print
    
###############################################################################

try:
    print("NOTE: if you wish to create a low priority alarm with 1 pulse enter frequency 0 here!")
    baseFrequency2 = input("Base frequency of 2nd pulse [" + str(baseFrequency_Hz_min) + "Hz; " + str(baseFrequency_Hz_max) + "Hz] (default: " + str(defaultBaseFrequency2) + "Hz): ")
except:
    baseFrequency2 = defaultBaseFrequency2

print("==> Selected base frequency of 2nd pulse: " + str(baseFrequency2))
# IEC 60601-1-8 page 17 requires base frequency in range [150Hz, 1000Hz]
if baseFrequency2 == 0:
    print("NOTE: Second pulse disabled!")
else:
    if (baseFrequency_Hz_min > baseFrequency2 or baseFrequency2 > baseFrequency_Hz_max):
        print("*** WARNING: pulse frequency f_0 out of range [150Hz, 1000Hz]")
print

harmonics2 = []
volumes2 = []

if baseFrequency2 != 0:
    # to keep this code simple we leave this task to the user: 
    # first harmonic is 1 and harmonics are sorted ascending.
    print("IMPORTANT NOTE: the first harmonic must be 1 and the harmonics must be in ascending order!!!")
    while len(harmonics2) != noHarmonics:
        harmonicsStr2 = raw_input(str(noHarmonics) + " Harmonics [positive integer] (default: " + harmonicsStr1 + "): ")
        if len(harmonicsStr2) == 0:
            harmonicsStr2 = harmonicsStr1 
            harmonics2 = harmonicsStr2.split()
            noHarmonics = len(harmonics2)

    print("==> Selected harmonics of 2nd pulse: " + harmonicsStr2)
   
    # hasEnoughHarmonics ensures the correct format of harmonics. 
    # Hence call before working on harmonics
    if (not hasEnoughHarmonics(baseFrequency2, harmonics2)):
        print("*** WARNING: less than required number of harmonics in range [300Hz, 4000Hz]")
    print

    ###############################################################################

    while len(volumes2) != noHarmonics:
        volumesStr2 = raw_input(str(noHarmonics) + " Volumes (default: " + volumesStr1 + "): ")
        if len(volumesStr2) == 0:
            volumesStr2 = volumesStr1
        volumes2 = getVolumes(volumesStr2)

    print("==> Selected volumes of 2nd pulse: " + volumesStr2)

    dBvalue=str(maxDiffSoundPressureToPulseFrequencyInDB)
    if (not hasSignificantVolumesInsideDbRange(volumes2, baseFrequency2, harmonics2)):
        print("*** WARNING: less than 4 harmonics with volumes +-" + dBvalue + "dB from base frequency's volume")
        print("            "),
        vOODbR = volumesOutOfDbRange(volumes2)
        print("             The following volumes differ more than " + dBvalue + "dB from base frequency's volume:")
        for v in vOODbR:
            print(str(v) + ", "),
    print

else:
    harmonicsStr2 = ''
    volumesStr2   = '' 
    
###############################################################################

try:
    burstSpacing_ms = input("Spacing between two bursts in ms [" + str(pulse.burstSpacing_ms_min) +  "ms; infinity) (default: " + str(defaultBurstSpacing_ms) + "ms): ")
except:
    burstSpacing_ms = defaultBurstSpacing_ms

print("==> Selected burst spacing: " + str(pulse.setBurstSpacing_ms(burstSpacing_ms)) + " ms")
if (not pulse.isBurstSpacingInRange()):
    print("*** WARNING: burst spacing out of range")
print

###############################################################################

try:
    print("Some devices require a silence period at the very start")
    print("which is beyond IEC 60601-1-8 compliance.")
    startWithSilence_ms = input("Silence at start in ms (default: " + str(defaultStartWithSilence_ms) + "ms): ")
except:
    startWithSilence_ms = defaultStartWithSilence_ms

startWithSilence_ms = max(0, startWithSilence_ms)
print("==> Selected silence at start: " + str(startWithSilence_ms) + " ms")
print

###############################################################################

doSave = 'y'
try:
    doSave = raw_input("Save parameters as new defaults [Y|n]? ")
except:
    doSave = 'y'

if (doSave != 'n' and doSave != 'N'):
    try:
        f=open(lpConfigFilename + ".py","w")
        f.write("#!/usr/bin/python"                                          + "\n" +
                "defaultSampleRate_Hz       = "   + str(sampleRate_Hz)       + "\n" +
                "defaultPulseSpacing_ms     = "   + str(pulseSpacing_ms)     + "\n" +
                "defaultPulseDuration_ms    = "   + str(pulseDuration_ms)    + "\n" +
                "defaultRiseTime_pc         = "   + str(riseTime_pc)         + "\n" +
                "defaultFallTime_pc         = "   + str(fallTime_pc)         + "\n" +
                "defaultBaseFrequency1      = "   + str(baseFrequency1)      + "\n" +
                "defaultHarmonicStr1        = \"" + str(harmonicsStr1)       + "\"\n" +
                "defaultVolumeStr1          = \"" + str(volumesStr1)         + "\"\n" +
                "defaultBaseFrequency2      = "   + str(baseFrequency2)      + "\n" +
                "defaultHarmonicStr2        = \"" + str(harmonicsStr2)       + "\"\n" +
                "defaultVolumeStr2          = \"" + str(volumesStr2)         + "\"\n" +
                "defaultBurstSpacing_ms     = "   + str(burstSpacing_ms)     + "\n"   +
                "defaultStartWithSilence_ms = "   + str(startWithSilence_ms) + "\n")
        f.close()
        print("Configuration saved in " + lpConfigFilename + ".py\n")
    except:
        print(lpConfigFilename + ".py locked by other application - please close\n")
        raw_input()

###############################################################################

print "\n#############################################\n"
print "\nDetermine max volume across all pulses"
maxVol1 = getMax(volumes1)
maxVol2 = getMax(volumes2)
maxVol  = max(maxVol1, maxVol2)    

if maxVol == 0:
    raise ValueError('volumes of all harmonics in pulses cannot be all 0')

###############################################################################

# create array of integer volumes and normalize volume across all volChar1+2
print "Normalizing volumes across pulses"

# it is maxVol != 0
for i, vol in enumerate(volumes1):
    volumes1[i] = vol / maxVol
for i, vol in enumerate(volumes2):
    volumes2[i] = vol / maxVol

###############################################################################

# pulse1/2 are arrays of harmonics
pulse1 = []
pulse2 = []

print "Creating wave and harmonics for pulse 1"
for i, volume in enumerate(volumes1):
    pulse1.append(pulse.createWave(baseFrequency1 * int(harmonics1[i]), volume))
print "Creating wave and harmonics for pulse 2"
for i, volume in enumerate(volumes2):
    pulse2.append(pulse.createWave(baseFrequency2 * int(harmonics2[i]), volume))

###############################################################################

print "Merging harmonics and creating final burst with 2 pulses"
# merge the audio files
audio = ([0.0] * pulse._getSamplesFromMs(startWithSilence_ms))

p1 = PulseMerger(pulse1)
p1Array = p1.merge()
print "Pulse 1:\t" + str(pulse.getPulseDuration_ms()) + "ms"
audio = audio + p1Array
maxAbs1 = p1.getMaxVolume()

if len(harmonicsStr2) != 0 and len(volumesStr2) != 0 and defaultBaseFrequency2 > 0 and pulseDuration_ms > 0:
    # IEC 60601-1-8 page 17 - silence btw Pulse 1 and 2: y = 125ms to 250ms
    # y is here called pulse_90pc_spacing_ms (see also wavetools.py)
    print "Silence 1:\t" + str(pulse.getPulseSpacing_ms()) + "ms"
    audio = audio + pulse.createSilence()

    p2 = PulseMerger(pulse2)
    print "Pulse 2:\t" + str(pulse.getPulseDuration_ms()) + "ms"
    audio = audio + p2.merge()
    maxAbs2 = p2.getMaxVolume()
else:
    maxAbs2 = 0

maxAbs = max(maxAbs1, maxAbs2)
# maxAbs != 0 since maxVol != 0

# IEC 60601-1-8 page 17 - silence btw two bursts: > 15.0 seconds
# here called burstSpacing_ms
print "Silence 2:\t" + str(pulse.getBurstSpacing_ms()) + "ms"
audio = audio + pulse.createSilence(pulse.getBurstSpacing_ms())
  
###############################################################################

# checking IEC 60601-1-8 Table 3:
maxDiffSoundPressureAnyPulsesInDB=10
maxDiffSoundPressureAnyPulses=10.0**(maxDiffSoundPressureAnyPulsesInDB/20.0)
# Max difference in amplitude between any two PULSES is 10dB (as factor: 3.16)
if maxAbs2 != 0 and maxAbs1 / maxAbs2 > maxDiffSoundPressureAnyPulses:
    print("*** WARNING: more than " + maxDiffSoundPressureAnyPulses + "dB difference in amplitude between pulses\n")
if maxAbs1 != 0 and maxAbs2 / maxAbs1 > maxDiffSoundPressureAnyPulses:
    print("*** WARNING: more than " + maxDiffSoundPressureAnyPulses + "dB difference in amplitude between pulses\n")

###############################################################################

print "Setting max gain across burst to " + str(gain)
  
# set the volume of the final output here:
if maxAbs != 0:
    scale = gain / maxAbs
else:
    scale = 0

for i, sample in enumerate(audio):
    audio[i] = sample * scale

###############################################################################

print "Saving wave in " + outputFilePath

save_wav(audio, outputFilePath, sampleRate_Hz)

###############################################################################

if remoteSCPtarget != None:
    print "Copying " + outputFilePath + " to " + remoteSCPtarget
    subprocess.check_output(['scp', outputFilePath, remoteSCPtarget])

print("All Done!")
