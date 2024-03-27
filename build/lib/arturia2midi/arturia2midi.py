import json
import re
import pretty_midi
from json_repair import repair_json
from tomark import Tomark


# Function to load a JSON file
def load_json_file(file_path):
    with open(file_path, "r") as file:
        json_string = file.read()

        # Using repair_json library here because the default output from
        # Arturia is an incorrectly formatted JSON file
        return json.loads(repair_json(json_string))


# Function to decode a single key using the parameters data
def decode_key(key, parameters_data):
    # Extract the parameter ID from the key
    match = re.match(r"(\d+)_(\d+)", key)
    if match:
        param_id = int(match.group(2))

        # Find the corresponding parameter in the parameters data
        for param in parameters_data["fields"]:
            if param["paramId"] == param_id:
                if "comment" in param:
                    return f'{param["name"]} ({param["comment"]})'
                else:
                    return param["name"]
    return "Unknown parameter"


def calculate_tempo(tempo, key, value):
    """
        Decoding Tempo
        Tempo is determined by combining three fields for least-significant
        bits (LSB), middle significance bits (MidSB) and most significant
        bits (MSB).  For example, a tempo of 120.00 is represented in the
        three fields as follows:

                Key: Value                    Binary
            - 120_70: 96    (MSB)       ->  1100000
            - 120_71: 93    (MidSB)     ->  1011101
            - 120_72: 0     (LSB)       ->  0000000

            Combined binary             ->  110000010111010000000
            In decimal                  ->  12000
            / 100 for Tempo             ->  120.00
    """

    if key == "120_70":
        # Project tempo part 3 (LSB)
        tempo['lsb'] = bin(value)
    elif key == "120_71":
        # Project tempo part 2 (MidSB)
        tempo['mdsb'] = bin(value)
    elif key == "120_72":
        # Project tempo part 1 (MSB)
        tempo['msb'] = bin(value)

    if (
        tempo['msb'] is not None
        and tempo['mdsb'] is not None
        and tempo['lsb'] is not None
    ):
        tempobin = (
            tempo['msb']
            + tempo['mdsb'].replace("0b", "")
            + tempo['lsb'].replace("0b", "")
        )
        tempo['project'] = float(int(tempobin, 2) / 100)
        return tempo
    else:
        return tempo


def decode_track_id(track_id):
    return {
        "version": "device",
        "device": "device",
        "120": "project",
        "121": "state",
        "122": "control",
        "123": "track1",
        "124": "track2",
        "125": "track3",
        "126": "track4",
    }.get(track_id, "unknown")


def update_track(decoded_project, track, key, value, decoded_key):

    # Setting pattern, mult, and note to 0 if there is no value
    pattern_id = "0"
    multiplier = "0"
    note_id = "0"
    sections = key.split('_')
    ptrack = decoded_project[track]

    # Break sections into variables
    if len(sections) == 2:
        param_id = sections[1]
    elif len(sections) == 3:
        param_id, pattern_id = sections[1:]
    elif len(sections) == 4:
        param_id, pattern_id, multiplier = sections[1:]
    if len(sections) == 5:
        param_id, pattern_id, multiplier, note_id = sections[1:]

    # Parse the param_id, there always should be one
    if param_id not in ptrack:
        ptrack[param_id] = {}
    if pattern_id not in ptrack[param_id]:
        ptrack[param_id][pattern_id] = {}
    if multiplier not in ptrack[param_id][pattern_id]:
        ptrack[param_id][pattern_id][multiplier] = {}
    if note_id not in ptrack[param_id][pattern_id][multiplier]:
        ptrack[param_id][pattern_id][multiplier][note_id] = {}

    ptrack[param_id]["desc"] = decoded_key
    ptrack[param_id][pattern_id][multiplier][note_id]["value"] = value
    ptrack[param_id][pattern_id][multiplier][note_id]["key"] = key

    return ptrack


def decode_project_file(project_file_path, parameters_file_path):
    # Load the project and parameters files
    project_data = load_json_file(project_file_path)
    parameters_data = load_json_file(parameters_file_path)
    decoded_project = {
        "device": {},
        "project": {},
        "state": {},
        "control": {},
        "track1": {},
        "track2": {},
        "track3": {},
        "track4": {},
    }
    tempo = {
        'project': None,
        'lsb': None,
        'mdsb': None,
        'msb': None
    }
    swing = None

    # Iterate over each item in the project file
    for key, value in project_data.items():

        # Get the track name from track ID
        track = decode_track_id(key.split("_")[0])

        # Handle device and unknown tracks
        if track == "device":
            decoded_project["device"][key] = value
            continue
        if track == "unknown":
            continue

        # Calculate the tempo
        if track == "project" and tempo['project'] is None:
            tempo = calculate_tempo(tempo, key, value)
            if tempo['project']:
                decoded_project[track]['tempo'] = tempo['project']
                print(f"Detected Tempo: {tempo['project']:.2f}")

        # Find swing parameter
        if track == "project" and swing is None:
            if key == "120_74":
                swing = value
                decoded_project[track]["swing"] = swing
                continue

        """
        TODO: Determine if Track 1 is in SEQ or DRUM mode:

        This parameter is set per pattern, but a limitation in MIDI allows us
        to only set one instrument type per track. Therefore, we'll derive the
        mode from the first pattern in the track.

        The value for SEQ/DRUM mode is derived from the first bit in the value
        of Parameter ID 100. For example, for Track 1 (123), Pattern 1 (1):

            Key: Value              Binary
            123_100_1: 26       ->  00011010
        """

        # Get the description for the parameter
        decoded_key = decode_key(key, parameters_data)
        decoded_project[track] = update_track(
            decoded_project, track, key, value, decoded_key
        )

    return decoded_project


def calculate_track_steps(decoded_track, is_drum):

    # It's important to determine if Track 1 is DRUM or SEQ, because the
    # Parameter IDs that we need to fetch are going to be different

    if is_drum:
        # Parameter ID 54:  DRUM step corresponding step
        steps = decoded_track["54"]
        # Parameter ID 117: DRUM note pitch
        pitches = decoded_track["117"]
        # Parameter ID 118: DRUM note gate length
        gates = decoded_track["118"]
        # Parameter ID 119: DRUM note velocity
        velocities = decoded_track["119"]
    else:
        # Parameter ID 50:  Seq note corresponding step
        steps = decoded_track["50"]
        # Parameter ID 109: Seq note pitch
        pitches = decoded_track["109"]
        # Parameter ID 110: Seq note gate length
        gates = decoded_track["110"]
        # Parameter ID 111: Seq note velocity
        velocities = decoded_track["111"]

    # We have to derive the active steps from Parameter ID 54 or 50 before we
    # can iterate on them and fill them in with pitch, gate, and velocity
    track_steps = {}

    # Calculate the steps with actual notes on them in the pattern
    for pattern, data in steps.items():
        pattern_note_steps = {}
        if pattern != "desc":
            for mult, subdata in data.items():
                # Still need to figure out what the mult data is for
                if mult == "1":

                    for note, step in subdata.items():
                        if step["value"] != 127:

                            if int(step["value"]) not in pattern_note_steps:
                                pattern_note_steps[int(step["value"])] = {}
                            if is_drum:
                                # Transpose the drums to match General MIDI
                                pitch = int(
                                    pitches[pattern][mult][note]["value"]
                                    ) + 36
                            else:
                                pitch = int(
                                    pitches[pattern][mult][note]["value"]
                                    )

                            pattern_note_steps[int(step["value"])][note] = {
                                "pitch": pitch,
                                "velocity": int(
                                    velocities[pattern][mult][note]["value"]
                                ),
                                "gate": int(
                                    gates[pattern][mult][note]["value"]
                                    ),
                            }

            track_steps[int(pattern)] = pattern_note_steps
        else:
            continue

    return track_steps


def track_to_instrument(track_data, track, bpm, is_drum):

    # Create an Instrument instance
    # I'd like to offer support for changing this based on user choice
    if is_drum:
        instrument = pretty_midi.Instrument(is_drum=is_drum, program=0)
    else:
        instrument = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program(
                "Acoustic Grand Piano"
                )
        )

    # Set the sixteenth note length based on the tempo we derived
    sixteenth_note_duration = 60 / (bpm * 2)

    # Keep a cursor so we know when the current pattern ends
    pattern_cursor = 0

    # For a list of patterns with data in them
    pattern_list = []

    # Pattern Length
    pattern_end = 64 * sixteenth_note_duration

    # Loop through the patterns
    for pattern, step_info in track_data.items():

        # Add the pattern ID to the list of patterns with data in them
        if step_info != {}:
            pattern_list.append(pattern)

        # Loop through the step info in the patterns
        for step, note_info in step_info.items():
            # Loop through the note info associated with the steps
            for note_id, attrs in note_info.items():
                # Calculate the start time for the note
                start_time = (
                    step * sixteenth_note_duration
                    + pattern_cursor * sixteenth_note_duration
                )

                # Calculate the end time based on the gate value
                end_time = start_time + (
                    (attrs["gate"] / 2) * sixteenth_note_duration
                    )

                # Cropping notes that are held too long
                if not is_drum and end_time > pattern_end:
                    end_time = pattern_end

                # Create a new Note object for this note
                note = pretty_midi.Note(
                    velocity=attrs["velocity"],
                    pitch=attrs["pitch"],
                    start=start_time,
                    end=end_time,
                )

                # Add the note to the instrument
                instrument.notes.append(note)

        # Increment the cursor by pattern length (defaulting to 64 for now)
        # TODO: Decode pattern length
        pattern_cursor = pattern_cursor + 64
        pattern_end = pattern_end + pattern_end

    print(f"Patterns in {track}: {pattern_list}")

    return instrument


def to_midi_track(midi_data, decoded_track, track, is_drum):

    # Grab the Project's tempo parameter that we derived earlier
    bpm = decoded_track["project"]["tempo"]

    # Copy just the information for a specific track
    decoded_track = decoded_track[track]

    # Figure out which steps in the track actually have notes
    track_steps = calculate_track_steps(decoded_track, is_drum)

    # It helps later to sort the track data by pattern ID
    track_data = dict(sorted(track_steps.items()))

    # Convert the track data to a PrettyMIDI instrument
    instrument = track_to_instrument(track_data, track, bpm, is_drum)

    # Add the instrument to the PrettyMIDI object
    midi_data.instruments.append(instrument)

    return midi_data


def parameters_to_markdown(decoded_project_data):
    params = []
    tracks = ["device", "project", "track1", "track2", "track3", "track4"]
    for track in tracks:

        for param_id, value in decoded_project_data[track].items():
            if track == "device" or (
                track == "project" and (
                    param_id == "tempo" or param_id == "swing"
                    )
            ):
                continue
            elif "desc" in value:
                param = {}
                param["id"] = int(param_id)
                param["desc"] = value["desc"]
                params.append(param)

    # dedup
    params = [dict(t) for t in {tuple(d.items()) for d in params}]

    # sort by ID
    params = sorted(params, key=lambda d: d["id"])

    # convert to markdown table
    markdown = Tomark.table(params)

    return markdown