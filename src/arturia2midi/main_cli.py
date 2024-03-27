import argparse
import json
import pretty_midi
import sys

from .arturia2midi import (
    decode_project_file,
    parameters_to_markdown,
    to_midi_track
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--device",
    "-d",
    type=str,
    default="KeyStepPro",
    help="Coded name of the device to decode data for, eg. KeyStepPro",
)
parser.add_argument(
    "--project",
    "-p",
    type=str,
    default="Sample",
    help="Name of a project to decode, eg. Sample",
)
parser.add_argument(
    "--markdown",
    "-t",
    action="store_true",
    default=False,
    help="Print a markdown table of all Parameter IDs",
)
parser.add_argument(
    "--midi",
    "-m",
    type=str,
    default="Sample.mid",
    help="Enable MIDI export and path to output file, eg. Sample.mid",
)
parser.add_argument(
    "--json",
    "-j",
    type=str,
    help="Enable JSON dump and path to output file, eg. Sample.json",
)
args = parser.parse_args()

print("\narturia2midi - 0.0.1\n")

if args.midi == "Sample.mid" and args.project == "Sample":
    print("Using Sample data!")

# Paths to your project and parameters (preferences) files
project_file_path = f"Projects/{args.project}.{args.device}"
print(f"Reading project file {project_file_path}")
parameters_file_path = f"Devices/{args.device}.json"
print(f"Reading parameters file {parameters_file_path}")

# Decode the project file
decoded_project_data = decode_project_file(
    project_file_path, 
    parameters_file_path
)

if args.midi:
    # Initialize PrettyMIDI object
    midi_data = pretty_midi.PrettyMIDI(
        initial_tempo=decoded_project_data["project"]["tempo"]
    )
    for i in range(1, 5):
        if i == 1:
            is_drum = True
            print(f"Converting track{i} DRUM to MIDI")
        else:
            is_drum = False
            print(f"Converting track{i} SEQ to MIDI")
        midi_data = to_midi_track(
            midi_data, decoded_project_data, f"track{i}", is_drum
        )

    # Write out the MIDI data to a new file
    midi_data.write(f"MIDI/{args.midi}")
    print(f"MIDI written to MIDI/{args.midi}!")

# Output or process the decoded project data for debugs
if args.json:
    json_out = json.dumps(decoded_project_data, indent=4, sort_keys=True)
    with open(f"JSON/{args.json}", "w") as fp:
        fp.write(json_out)

    print(f"Decoded project written to JSON/{args.json}!")

if args.markdown:
    markdown = parameters_to_markdown(decoded_project_data)
    print("\nParameter ID Markdown Table")
    print("-----------------------------")
    print(markdown)

print(f"Success!\n")

sys.exit()
