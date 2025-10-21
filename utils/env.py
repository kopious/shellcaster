import os
from pathlib import Path
import os
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv, set_key

# Global flag to track if .env has been loaded
_env_loaded = False

def ensure_env_loaded():
    """Ensure .env file is loaded."""
    global _env_loaded
    if not _env_loaded:
        # Try to find .env file in current or parent directories
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            env_path = parent / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                _env_loaded = True
                return
        # If no .env found, still mark as loaded to avoid repeated searches
        _env_loaded = True

def get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable.
    
    Args:
        var_name: Name of the environment variable
        default: Default value to return if variable is not found
        
    Returns:
        Value of the environment variable or default if not found
    """
    ensure_env_loaded()
    return os.getenv(var_name, default)

def set_env(var_name: str, value: Any) -> None:
    """
    Set an environment variable in both the current process and .env file.
    
    Args:
        var_name: Name of the environment variable
        value: Value to set (will be converted to string)
    """
    ensure_env_loaded()
    # Convert value to string
    str_value = str(value)
    
    # Set in current process
    os.environ[var_name] = str_value
    
    # Find .env file in current or parent directories
    env_path = None
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        potential_path = parent / '.env'
        if potential_path.exists():
            env_path = potential_path
            break
    
    # If no .env found, create one in current directory
    if env_path is None:
        env_path = current_dir / '.env'
    
    # Update .env file
    if env_path.exists():
        # Read existing content
        content = env_path.read_text()
        lines = content.splitlines()
        
        # Check if variable already exists
        var_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{var_name}="):
                lines[i] = f"{var_name}={str_value}"
                var_found = True
                break
        
        # If variable not found, add it
        if not var_found:
            lines.append(f"{var_name}={str_value}")
        
        # Write back to file
        env_path.write_text('\n'.join(lines) + '\n')
    else:
        # Create new .env file
        env_path.write_text(f"{var_name}={str_value}\n")
    
    # Ensure the .env file is reloaded
    global _env_loaded
    _env_loaded = False
    
    # Update the .env file
    set_key(env_path, var_name, str_value, quote_mode='never')
