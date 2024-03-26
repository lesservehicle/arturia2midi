# arturia2midi

Converts Arturia MIDI Control Center project files to MIDI files. Please take note of the following limitations:

- Only works on *.KeyStepPro files for the KeyStep Pro so far, because that's the device I own.
- Only **outputs** MIDI, no input. Yet.
- Parameter support is **very** limited:
    - Note pitch
    - Note gate
    - Note velocity
    - Project tempo
- Output can be buggy. I'm working on it!

## Installation

For each iteration of this project, I run `pip freeze > requirements.txt` after testing to make sure I've got version-locked pip packages, so you should be able to just fire it up by installing `requirements.txt`.

```
% pip install -r requirements.txt
```

Of course, I would instead recommend that you use a Python Virtual Environment, preferably with version 3.11. I like to use [PyEnv](https://github.com/pyenv/pyenv) to simplify this process for me:

```
% pyenv install 3.11.5
% pyenv virtualenv arturia2midi
% pyenv activate arturia2midi
% pip install -r requirements.txt
```

## File Formats for Devices and Projects

Device files are available from the resources folder for MIDI Control Center. I've included a few of them in the repo here, under the `Devices` folder. To support a device, copy the (DeviceName).json file to the `Devices` folder and specify it with `-d (DeviceName)`, eg. `-p KeyStepPro`.

Project files are exportable from MIDI Control Center, and typically have a file extension of `*.(DeviceName)`. For example, if I have a project called "FatBeats" on my KeyStep Pro and export it, the resultant file will be named `FatBeats.KeyStepPro`. Copy your project files into the `Projects` folder to enable them to be read and specify them with `-p (ProjectName)`, eg. `-p FatBeats`.

## Usage

```
% python main.py -h
usage: main.py [-h] [--device DEVICE] [--project PROJECT] [--markdown] [--midi MIDI] [--json JSON]

options:
  -h, --help            show this help message and exit
  --device DEVICE, -d DEVICE
                        Coded name of the device to decode data for, eg. KeyStepPro
  --project PROJECT, -p PROJECT
                        Name of a project to decode, eg. Sample
  --markdown, -t        Print a markdown table of all Parameter IDs
  --midi MIDI, -m MIDI  Enable MIDI export and provide path to output file, eg. Sample.mid
  --json JSON, -j JSON  Enable JSON dump of decoded keys and provide path to output file, eg. Sample.json
```

## Example of Full Usage

```
% python main.py -d KeyStepPro -p Sample -m Sample.mid -j Sample.json -t
Reading project file Projects/Sample.KeyStepPro
Reading parameters file Devices/KeyStepPro.json
Detected Tempo: 120.00
Converting Track 1 to MIDI
Patterns in track1: [1]
Converting Track 2 to MIDI
Patterns in track2: [1]
Converting Track 3 to MIDI
Patterns in track3: [1]
Converting Track 4 to MIDI
Patterns in track4: [1]
MIDI written to Sample.mid
Decoded project written to Sample.json
```

## To Do
- Support other Arturia devices
- Support for MIDI conversion to Project file
- Support for more parameters, eventually getting all of them.

# KeyStep Pro Data

The following is just me doing my best to interpret the data in the `KeyStepPro.json` file against a `*.KeyStepPro` project file. My current understanding is incomplete.

## Key Format

Keys in *.KeyStepPro files follow the pattern of `(Track)_(Parameter)_(Pattern)_(Unknown)_(Note)`. The purpose of the fourth slot in the key name is currently uknown to me, but always has three copies.

For example, the key `124_111_16_1_32` corresponds to the following:

| Parameter | Description |
|-------|-----|
| 124 | Track 2 | 
| 111 | Seq note velocity (See table below)
| 16 | Pattern 16
| 1 | Unknown |
| 32 | Note/Step 32 |

## Tracks 

| ID | Track |
|-------|-----|
| 120 | Project Settings |
| 121 | State Settings |
| 122 | Control Settings |
| 123 | Track 1 SEQ or DRUM |
| 124 | Track 2 SEQ or ARP |
| 125 | Track 3 SEQ or ARP |
| 126 | Track 4 SEQ or ARP |

## Parameters
| ID | Description |
|-----|-----|
| 20 | Pattern Seq Program Change Value (Program Change Value (4 LSB) : bit 0 - 3) |
| 21 | Pattern Seq Program Change Value (Write flag : bit 6) |
| 22 | Pattern Seq Program Change Value MSB (Program Change Value MSB) |
| 23 | Pattern Seq Program Change Value LSB (Program Change Value LSB) |
| 25 | Pattern Drum Program Change Value (Program Change Value (4 LSB) : bit 0 - 3) |
| 26 | Pattern Drum Program Change Value (Write flag : bit 6) |
| 27 | Pattern Drum Program Change Value MSB (Program Change Value MSB) |
| 28 | Pattern Drum Program Change Value LSB (Program Change Value LSB) |
| 37 | Project data state (Project data state) |
| 39 | Track data state (Track data state) |
| 40 | Pattern data state (Pattern data state) |
| 48 | Step Seq step active |
| 49 | Step Seq step skip |
| 50 | Seq note corresponding step |
| 51 | DRUM poly step count |
| 52 | DRUM step active |
| 53 | DRUM step skip |
| 54 | DRUM step corresponding step |
| 55 | Track tranpose group (Is track in transpose group) |
| 56 | ARP swing (ARP swing) |
| 59 | Track seq color |
| 60 | Track drum color |
| 68 | ARP group 1 parameters (ARP track 3 size : bit 5 - 6) |
| 69 | ARP group 2 parameters (ARP track 4 size : bit 1 - 2) |
| 70 | Project tempo part 3 (LSB) (Tempo is divided into 3 part (MSB - MidSB - LSB)) |
| 71 | Project tempo part 2 (MidSB) (Tempo is divided into 3 part (MSB - MidSB - LSB)) |
| 73 | global BPM, metronome triplet, metronome size, wait to load in a bitfield (wait to load : bit 4) |
| 75 | Current scene |
| 85 | Track transposition state, transposition octave in a bitfield (transposition octave : bit 4 - 5 - 6) |
| 86 | Track keyboard octave, chord mode state, Arp/Drum mode state in a bitfield (Arp/Drum mode state : bit 6) |
| 87 | Chord |
| 97 | Pattern Seq swing (%) (an offset of 25 is applied to be send by MIDI) (-25% to +25%) |
| 98 | Pattern Seq step count |
| 99 | Pattern Seq triplet state, swing offset state, polyrythm state, step size, playback direction in a bitfield (playback direction : bit 5 - 6) |
| 100 | Pattern Seq ARP/Drum mode, ARP type, ARP octave in a bitfield (ARP octave : bit 4 - 5 - 6) |
| 101 | Pattern Seq user scale 1 part 3 (LSB) (User scale 1 is divided into 3 part (MSB - MidSB - LSB)) |
| 102 | Pattern Seq user scale 1 part 2 (MidSB) (User scale 1 is divided into 3 part (MSB - MidSB - LSB)) |
| 103 | Pattern Seq user scale 1 part 1 (MSB) (User scale 1 is divided into 3 part (MSB - MidSB - LSB)) |
| 104 | Pattern Seq user scale 2 part 3 (LSB) (User scale 2 is divided into 3 part (MSB - MidSB - LSB)) |
| 105 | Pattern Seq user scale 2 part 2 (MidSB) (User scale 2 is divided into 3 part (MSB - MidSB - LSB)) |
| 106 | Pattern Seq user scale 2 part 1 (MSB) (User scale 2 is divided into 3 part (MSB - MidSB - LSB)) |
| 107 | Pattern Seq root note |
| 108 | Pattern Seq scale |
| 109 | Seq note pitch |
| 110 | Seq note gate length |
| 111 | Seq note velocity |
| 112 | Seq note time shift |
| 113 | Seq note randomness |
| 114 | Pattern DRUM swing (%) (an offset of 25 is applied to be send by MIDI) (-25% to +25%) |
| 115 | Pattern DRUM step count |
| 116 | Pattern DRUM triplet state, swing offset state, polyrythm state, step size, playback direction in a bitfield (playback direction : bit 5 - 6) |
| 117 | DRUM note pitch |
| 118 | DRUM note gate length |
| 119 | DRUM note velocity |
| 120 | DRUM note time shift |
| 121 | DRUM note randomness |
| 122 | Track transposition |
| 123 | Track MIDI channel (Track MIDI channel of the project) |