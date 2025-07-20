#!/bin/zsh
set -euo pipefail

# Load your shell rc (for PATH)
source ~/.zshrc

# Grab Automator inputs
input_paths=("$@")

# Add Homebrew tools if needed
export PATH="/opt/homebrew/bin:$PATH"

# Change into your dejatext project folder
cd "$HOME/code/dejatext" || { echo "Missing $HOME/code/dejatext" >&2; exit 1; }

# Activate virtual environment
source .venv/bin/activate || { echo "Failed to activate virtual environment" >&2; exit 1; }

# Process each input, appending _cleanup for the output folder
for input in "${input_paths[@]}"; do
  # Get the directory and basename of the input
  input_dir=$(dirname "$input")
  input_name=$(basename "$input")
  
  # Create output folder name: input_name_cleanup
  output_folder="${input_dir}/${input_name}_cleanup"
  
  echo "Processing: $input"
  echo "Output folder: $output_folder"
  
  # Run dejatext_cleanup.py with the input directory
  python dejatext_cleanup.py "$input" --output-folder "$output_folder" --verbose
  
  echo "✅ Cleanup completed for: $input"
  echo "📁 Results saved to: $output_folder"
done

# Deactivate environment
deactivate

echo "🎉 All files processed successfully!" 