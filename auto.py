#!/usr/bin/env python3
"""
Git Script Sync - User Laptop Component
Syncs local ~/scripts folder to Git repository
"""

import os
import sys
import yaml
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import shutil


class GitScriptSync:
    def __init__(self, config_path="git_config.yaml"):
        self.config = self.load_config(config_path)
        self.scripts_path = self.get_scripts_path()
        self.repo_path = Path(self.config['git']['local_repo_path']).expanduser()
        
    def load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                return config
        except FileNotFoundError:
            print(f"❌ Config file '{config_path}' not found!")
            print("Please create git_config.yaml with your Git settings.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            sys.exit(1)
    
    def get_scripts_path(self):
        """Get the scripts folder path based on OS"""
        if platform.system() == "Windows":
            return Path.home() / "Scripts"
        else:  # Linux/Unix
            return Path.home() / "scripts"
    
    def run_git_command(self, command, cwd=None):
        """Run git command and return result"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=cwd or self.repo_path,
                capture_output=True, 
                text=True, 
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def setup_git_repo(self):
        """Clone or initialize Git repository"""
        repo_url = self.config['git']['repository_url']
        
        if self.repo_path.exists():
            print(f"📁 Using existing repo: {self.repo_path}")
            # Pull latest changes
            success, output = self.run_git_command("git pull origin main")
            if not success:
                print(f"⚠️  Warning: Could not pull latest changes: {output}")
            return True
        else:
            print(f"📥 Cloning repository to: {self.repo_path}")
            success, output = self.run_git_command(
                f"git clone {repo_url} {self.repo_path}",
                cwd=self.repo_path.parent
            )
            if success:
                print("✅ Repository cloned successfully")
                return True
            else:
                print(f"❌ Failed to clone repository: {output}")
                return False
    
    def copy_scripts_to_repo(self):
        """Copy all scripts from local folder to git repo"""
        if not self.scripts_path.exists():
            print(f"❌ Scripts directory not found: {self.scripts_path}")
            print(f"Please create the directory: {self.scripts_path}")
            return False
        
        # Get current user for folder organization
        current_user = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
        user_folder_in_repo = self.repo_path / current_user
        
        # Create user folder in repo if it doesn't exist
        user_folder_in_repo.mkdir(exist_ok=True)
        
        print(f"📁 Copying scripts to repo under: {current_user}/")
        
        excluded_extensions = self.config.get('sync', {}).get('exclude_extensions', ['.tmp', '.log', '.bak'])
        copied_files = 0
        
        # Walk through all app folders in scripts directory
        for item in self.scripts_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                app_folder = item.name
                target_app_folder = user_folder_in_repo / app_folder
                
                print(f"  📂 Processing app folder: {app_folder}")
                
                # Remove existing app folder in repo to ensure clean sync
                if target_app_folder.exists():
                    shutil.rmtree(target_app_folder)
                
                # Copy the entire app folder
                try:
                    shutil.copytree(item, target_app_folder)
                    
                    # Remove excluded files
                    for file_path in target_app_folder.rglob('*'):
                        if file_path.is_file():
                            if any(file_path.name.endswith(ext) for ext in excluded_extensions):
                                file_path.unlink()
                                print(f"    🗑️  Excluded: {file_path.name}")
                            else:
                                copied_files += 1
                                
                    print(f"    ✅ Copied app folder: {app_folder}")
                    
                except Exception as e:
                    print(f"    ❌ Error copying {app_folder}: {e}")
        
        print(f"📄 Total files copied: {copied_files}")
        return copied_files > 0
    
    def commit_and_push_changes(self):
        """Commit changes and push to remote repository"""
        current_user = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
        
        # Check if there are any changes
        success, output = self.run_git_command("git status --porcelain")
        if not success:
            print(f"❌ Error checking git status: {output}")
            return False
        
        if not output.strip():
            print("ℹ️  No changes to commit")
            return True
        
        print("📝 Changes detected, committing...")
        
        # Add all changes
        success, output = self.run_git_command("git add .")
        if not success:
            print(f"❌ Error adding files: {output}")
            return False
        
        # Commit with timestamp and user
        commit_message = f"Auto-sync scripts from {current_user} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        success, output = self.run_git_command(f'git commit -m "{commit_message}"')
        if not success:
            print(f"❌ Error committing: {output}")
            return False
        
        print("✅ Changes committed")
        
        # Push to remote
        branch_name = self.config['git'].get('branch', 'main')
        success, output = self.run_git_command(f"git push origin {branch_name}")
        if not success:
            print(f"❌ Error pushing to remote: {output}")
            return False
        
        print("✅ Changes pushed to remote repository")
        return True
    
    def sync_to_git(self):
        """Main sync function"""
        print(f"\n🚀 Starting Git sync at {datetime.now()}")
        print("=" * 50)
        
        # Step 1: Setup Git repository
        if not self.setup_git_repo():
            return False
        
        # Step 2: Copy scripts to repo
        if not self.copy_scripts_to_repo():
            print("ℹ️  No scripts to sync")
            return True
        
        # Step 3: Commit and push changes
        if not self.commit_and_push_changes():
            return False
        
        print("\n" + "=" * 50)
        print(f"🎉 Git sync completed successfully at {datetime.now()}")
        return True


def create_sample_git_config():
    """Create a sample Git configuration file"""
    current_user = os.getenv('USER') or os.getenv('USERNAME') or 'user'
    
    sample_config = {
        'git': {
            'repository_url': 'https://github.com/yourcompany/scripts-repo.git',
            'local_repo_path': f'~/scripts-git-repo',
            'branch': 'main'
        },
        'sync': {
            'exclude_extensions': ['.tmp', '.log', '.bak', '.swp', '.DS_Store'],
        }
    }
    
    with open('git_config.yaml', 'w') as file:
        yaml.dump(sample_config, file, default_flow_style=False, indent=2)
    
    print("📝 Created sample git_config.yaml")
    print("Please edit git_config.yaml with your Git repository details:")
    print("  - repository_url: Your Git repository URL")
    print("  - local_repo_path: Where to store the local Git repo")
    print("  - branch: Git branch to use (usually 'main')")
    print("\nMake sure you have Git credentials configured:")
    print("  git config --global user.name 'Your Name'")
    print("  git config --global user.email 'your.email@company.com'")


def main():
    """Main entry point"""
    
    # Check if config exists
    if not os.path.exists('git_config.yaml'):
        print("⚠️  Git configuration file not found!")
        response = input("Create sample git_config.yaml? (y/n): ").lower().strip()
        if response == 'y':
            create_sample_git_config()
            print("\nPlease edit git_config.yaml and run the script again.")
            return
        else:
            print("Cannot proceed without configuration.")
            return
    
    # Check if Git is installed
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Git is not installed or not in PATH")
        print("Please install Git:")
        print("  Windows: Download from https://git-scm.com/")
        print("  Linux: sudo apt install git (Ubuntu) or sudo yum install git (CentOS)")
        print("  Mac: brew install git")
        return
    
    # Initialize and run sync
    try:
        syncer = GitScriptSync()
        success = syncer.sync_to_git()
        
        if success:
            print("\n🎉 All scripts synced to Git successfully!")
        else:
            print("\n⚠️  Some operations failed. Check the output above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Sync interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
