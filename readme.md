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

```
% pip install -r requirements.txt
```

## Usage
```
% python main.py -h

usage: main.py [-h] [--instrument INSTRUMENT] [--project PROJECT] [--midi MIDI] [--json JSON]

options:
  -h, --help            show this help message and exit
  --instrument INSTRUMENT, -i INSTRUMENT
  --project PROJECT, -p PROJECT
  --midi MIDI, -m MIDI
  --json JSON, -j JSON
```

- **-i/--instrument** looks for Instrument information in the `Instruments` folder, defaults to "KeyStepPro"
- **-p/--project** looks for a project with the name you specify file with the specified instrument as the file extension in the `Projects` folder, eg. "Sample" looks for `Projects/Sample.KeyStepPro`.
- **-m/--midi** is the file path to your exported MIDI file, defaults to `Sample.mid`
- **-j/--json** is the file path to a JSON file which is the decoded project file

## Example

```
% python main.py -i KeyStepPro -p Sample -m Sample.mid -j Sample.json
Detected Tempo: 120.0
MIDI written to Sample.mid
```

## To Do
- Support other Arturia devices
- Support for MIDI conversion to Project file
- Support for more parameters, eventually getting all of them.