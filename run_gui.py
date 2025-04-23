#!/usr/bin/env python3
"""
Run script for the Anki Generator GUI.
This script sets up the Python path correctly before running the GUI.
"""

import sys
import os
import subprocess
import importlib.util

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Create a symbolic link for config.py if it doesn't exist
config_link_path = os.path.join(current_dir, 'config.py')
config_source_path = os.path.join(current_dir, 'src', 'config.py')

# Check if we need to create a symbolic link for config
if not os.path.exists(config_link_path) and os.path.exists(config_source_path):
    try:
        # For Windows, use copy instead of symlink if symlinks not supported
        if os.name == 'nt':
            import shutil
            shutil.copy2(config_source_path, config_link_path)
            print(f"Created a copy of {config_source_path} at {config_link_path}")
        else:
            # For Unix-like systems, create a symbolic link
            os.symlink(config_source_path, config_link_path)
            print(f"Created symbolic link from {config_source_path} to {config_link_path}")
    except Exception as e:
        print(f"Warning: Could not create config link: {e}")

# We also need to handle other imports like llm_generator, image_generator, and audio_generator
for module_name in ['llm_generator', 'image_generator', 'audio_generator']:
    link_path = os.path.join(current_dir, f'{module_name}.py')
    source_path = os.path.join(current_dir, 'src', f'{module_name}.py')
    
    if not os.path.exists(link_path) and os.path.exists(source_path):
        try:
            if os.name == 'nt':
                import shutil
                shutil.copy2(source_path, link_path)
                print(f"Created a copy of {source_path} at {link_path}")
            else:
                os.symlink(source_path, link_path)
                print(f"Created symbolic link from {source_path} to {link_path}")
        except Exception as e:
            print(f"Warning: Could not create {module_name} link: {e}")

# Run the GUI with the correct Python path
env = os.environ.copy()
env['PYTHONPATH'] = current_dir

# Create a subprocess to run the gui.py with the updated PYTHONPATH
subprocess.run([sys.executable, os.path.join('src', 'gui.py')], env=env) 