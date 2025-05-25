#!/bin/bash

# Initialize an empty array to store existing file paths
files=()

# out current directory
echo "Current directory: $(pwd)"

# goto the directory where the script is located
cd tests || { echo "Failed to change directory to 'tests'"; exit 1; }
echo "Changed directory to: $(pwd)"


# Loop through potential file numbers
# We'll try to find files with 1, 2, or 3 digits (e.g., turn_1.wav, turn_01.wav, turn_001.wav)
for i in {1..123}; do
    # Try non-padded filename first (e.g., turn_1.wav)
    filename_nopad="turn_${i}.wav"
    if [ -f "$filename_nopad" ]; then
        files+=("$filename_nopad")
        echo "Found: $filename_nopad" # Debug output
        continue # Move to the next number if found
    fi

    # Try zero-padded to two digits (e.g., turn_01.wav)
    # This will only apply for i < 10
    if [ "$i" -lt 10 ]; then
        filename_pad2="turn_0${i}.wav"
        if [ -f "$filename_pad2" ]; then
            files+=("$filename_pad2")
            echo "Found: $filename_pad2" # Debug output
            continue
        fi
    fi

    # Try zero-padded to three digits (e.g., turn_001.wav)
    # This will apply for all numbers, but is most common for i < 100
    if [ "$i" -lt 100 ]; then # Only try 3-digit padding for numbers that would benefit
        filename_pad3=$(printf "turn_%03d.wav" "$i")
        if [ -f "$filename_pad3" ]; then
            files+=("$filename_pad3")
            echo "Found: $filename_pad3" # Debug output
            continue
        fi
    fi

    echo "Not found: turn_${i}.wav (or its padded variants)" # Debug output for missing files
done

# Check if any files were found
if [ ${#files[@]} -eq 0 ]; then
    echo "Error: No matching 'turn_*.wav' files found in the current directory with common naming conventions."
    echo "Please ensure the script is run in the correct directory and filenames are like 'turn_1.wav', 'turn_01.wav', or 'turn_001.wav'."
    exit 1
fi

# Pass the existing files to sox
echo "Concatenating ${#files[@]} files into scenario.wav..."
sox --combine concatenate "${files[@]}" scenario1.wav

echo "Concatenation complete: scenario1.wav"
