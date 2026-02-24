#!/usr/bin/env python3

# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Complete Parse-Catalog Demo with Real API Calls.

This script demonstrates the full parse-catalog workflow by:
1. Making actual API calls using requests
2. Using the real catalog_rhel.json file
3. Showing all responses and generated artifacts
4. Interactive step-by-step execution with user confirmation

Usage:
    python buildstream_demo.py                           # Register new client
    python buildstream_demo.py --cleanup                  # Clean artifacts and register new client
    python buildstream_demo.py --help                     # Show options

    Note: Update the Configuration constants in code as per your configuration
"""

import argparse
import base64
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
import urllib3

import requests

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration constants
BASE_URL = "https://182.10.5.157:8010"
CLIENT_NAME = "demo-client"
AUTH_USERNAME = "admin"
AUTH_PASSWORD = ""
CREDENTIALS_FILE = Path(__file__).parent / "demo_client_credentials.json"

BUILD_STREAM_ARTIFACT_ROOT = "/opt/omnia/build_stream/artifacts"
CATALOG_FILE = Path("/opt/omnia/windsurf/working_dir/demo/catalog_rhel.json")

class ParseCatalogDemo:
    """Complete demo class for parse-catalog functionality."""

    def __init__(self, cleanup=False):
        self.base_url = BASE_URL

        # Client configuration
        self.client_name = CLIENT_NAME

        # Build Stream artifact root
        self.build_stream_artifact_root = BUILD_STREAM_ARTIFACT_ROOT

        # Authentication credentials for build_stream registration
        # These are the credentials used to register new OAuth clients
        self.auth_username = AUTH_USERNAME
        self.auth_password = AUTH_PASSWORD

        # Creates this file if it doesn't exist, for future use,
        # if exists it uses the client_id and client_secret from it
        self.credentials_file = CREDENTIALS_FILE

        self.catalog_file = CATALOG_FILE

        # Load existing credentials or set to None
        self.client_id = None
        self.client_secret = None
        self.load_credentials()

        self.access_token = None
        self.job_id = None
        self.correlation_id = str(uuid.uuid4())
        self.cleanup = cleanup

    def wait_for_enter(self, message="Press ENTER to continue..."):
        """Wait for user to press enter."""
        input(f"\n⏸️  {message}")

    def load_credentials(self):
        """Load client credentials from file if exists."""
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
                    client_id = credentials.get('client_id')
                    client_secret = credentials.get('client_secret')

                    # Only update if values are not empty
                    if client_id:
                        self.client_id = client_id
                    if client_secret:
                        self.client_secret = client_secret

                    print(f"📁 Loaded existing credentials from {self.credentials_file}")
                    return True
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Error loading credentials: {e}")
                return False
        return False

    def save_credentials(self, client_id, client_secret):
        """Save client credentials to file."""
        try:
            credentials = {
                'client_id': client_id,
                'client_secret': client_secret,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2)
            print(f"💾 Saved credentials to {self.credentials_file}")
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error saving credentials: {e}")
            return False

    def cleanup_artifacts(self):
        """Delete all contents inside build_stream_artifact_root."""
        print("\n" + "="*60)
        print("🧹 CLEANUP: Removing Existing Artifacts")
        print("="*60)

        artifacts_path = Path(self.build_stream_artifact_root)

        if not artifacts_path.exists():
            print(f"📂 Artifacts directory does not exist: {artifacts_path}")
            print("✅ Nothing to clean up")
            return

        print(f"� Artifacts Directory: {artifacts_path}")
        print("⚠️  This will delete all contents inside the artifacts directory")

        self.wait_for_enter("Press ENTER to proceed with cleanup...")

        try:
            # Delete all contents inside the directory
            deleted_count = 0
            for item in artifacts_path.iterdir():
                if item.is_dir():
                    print(f"🗑️  Removing directory: {item.name}/")
                    shutil.rmtree(item)
                    deleted_count += 1
                else:
                    print(f"🗑️  Removing file: {item.name}")
                    item.unlink()
                    deleted_count += 1

            print(f"\n✅ Cleanup completed: {deleted_count} items removed")

        except (OSError, shutil.Error) as e:
            print(f"\n❌ Cleanup failed: {e}")
            print("⚠️  Continuing with demo...")

    def check_server_health(self):
        """Check if the server is running."""
        print("\n" + "="*60)
        print("🏥 STEP 0: Health Check")
        print("="*60)
        print(f"📡 Endpoint: GET {self.base_url}/health")

        self.wait_for_enter("Press ENTER to check server health...")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5, verify=False)
            print(f"\n✅ Response Status: {response.status_code}")
            print(f"📝 Response Body: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Server not running at {self.base_url}")
            print("   Start server with: uvicorn main:app --host 0.0.0.0 --port 8010")
            return False
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"\n❌ Error: {e}")
            return False

    def register_client(self):
        """Register OAuth client or use existing one."""
        print("\n" + "="*60)
        print("📝 STEP 1: Register OAuth Client")
        print("="*60)

        # If we already have credentials, skip registration
        if self.client_secret:
            print("✅ Using provided credentials!")
            print(f"   Client ID: {self.client_id}")
            print(f"   Client Secret: {self.client_secret}")
            print("\n💡 Skipping registration - using existing credentials")
            return True

        # Authentication credentials for build_stream registration
        # These are the credentials used to register new OAuth clients
        # The vault shows: username="build_stream_register" with password_hash for "dell1234"
        # But the actual system might be using different credentials
        print(f"🔐 Using auth credentials: {self.auth_username}:"
              f"{self.auth_password}")
        auth_header = base64.b64encode(f"{self.auth_username}:{self.auth_password}".encode()).decode()

        client_data = {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "allowed_scopes": ["catalog:read", "catalog:write","job:write"],
            "grant_types": ["client_credentials"]
        }

        print(f"📡 Endpoint: POST {self.base_url}/api/v1/auth/register")
        print("📝 Headers:")
        print("   Content-Type: application/json")
        print(f"   Authorization: Basic {auth_header}")
        print("📝 Request Body:")
        print(json.dumps(client_data, indent=2))

        self.wait_for_enter("Press ENTER to register client...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                json=client_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_header}"
                },
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                client_info = response.json()
                print("📋 Response Body:")
                # Mask the secret for display
                display_info = client_info.copy()
                if 'client_secret' in display_info:
                    display_info['client_secret'] = display_info['client_secret'][:8] + "..." + display_info['client_secret'][-4:]
                print(json.dumps(display_info, indent=2))

                self.client_secret = client_info.get('client_secret')
                self.client_id = client_info.get('client_id')  # Use server-assigned ID
                print("\n✅ Client registered successfully!")
                print(f"   Client ID: {self.client_id}")
                print(f"   Client Secret: {self.client_secret}")

                # Save credentials to file for future use
                self.save_credentials(self.client_id, self.client_secret)

                print(f"\n💡 Credentials saved to {self.credentials_file}")
                print("💡 Next run will automatically use these credentials!")
                return True
            elif response.status_code == 409:
                # Client already exists, try to use existing one
                print("📋 Response Body:")
                print(response.text)
                print("\n⚠️  Client registration failed (max clients reached)")
                print("💡 Attempting to use existing client...")

                # Try to get token with a known existing client
                existing_client_id = "bld_daa6c90eff86b1036c9f922a098562e5"
                existing_client_secret = "bld_s_bUrHRr663yUldYraSQ1sDEWyR7x2x_6gPrVomUpnFtw"

                # Test if existing client works
                token_data = {
                    "grant_type": "client_credentials",
                    "client_id": existing_client_id,
                    "client_secret": existing_client_secret
                }

                token_response = requests.post(
                    f"{self.base_url}/api/v1/auth/token",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30,
                    verify=False
                )

                if token_response.status_code == 200:
                    self.client_id = existing_client_id
                    self.client_secret = existing_client_secret
                    print("✅ Using existing client!")
                    print(f"   Client ID: {self.client_id}")
                    print(f"   Client Secret: {self.client_secret}")
                    print("\n💡 These credentials are working for this session")
                    return True
                else:
                    print("❌ Existing client also failed")
                    return False
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Registration failed")
                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def get_access_token(self):
        """Get JWT access token."""
        print("\n" + "="*60)
        print("🔑 STEP 2: Get Access Token")
        print("="*60)

        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        print(f"📡 Endpoint: POST {self.base_url}/api/v1/auth/token")
        print("📋 Headers:")
        print("   Content-Type: application/x-www-form-urlencoded")
        print("📋 Request Body:")
        print("   grant_type=client_credentials")
        print(f"   client_id={self.client_id}")
        print(f"   client_secret={self.client_secret[:8]}...{self.client_secret[-4:]}")

        self.wait_for_enter("Press ENTER to get access token...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                token_info = response.json()
                self.access_token = token_info.get("access_token")

                # Mask token for display
                display_info = token_info.copy()
                if 'access_token' in display_info:
                    display_info['access_token'] = display_info['access_token'][:20] + "..." + display_info['access_token'][-10:]

                print("📋 Response Body:")
                print(json.dumps(display_info, indent=2))
                print("\n✅ Access token obtained!")
                return True
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Token request failed")

                # Check if this is an authentication error (401/403)
                if response.status_code in [401, 403]:
                    print("\n🔄 The access token request failed with authentication error.")
                    print("💡 This might be due to expired or invalid client credentials.")
                    return "retry_register"

                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def create_job(self):
        """Create a job for parse-catalog."""
        print("\n" + "="*60)
        print("🧾 STEP 3: Create Job")
        print("="*60)

        job_data = {
            "correlation_id": self.correlation_id,
            "client_id": self.client_id
        }

        idempotency_key = str(uuid.uuid4())

        print(f"📡 Endpoint: POST {self.base_url}/api/v1/jobs")
        print("📋 Headers:")
        print("   Content-Type: application/json")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")
        print(f"   Idempotency-Key: {idempotency_key}")
        print("📋 Request Body:")
        print(json.dumps(job_data, indent=2))

        self.wait_for_enter("Press ENTER to create job...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs",
                json=job_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                    "Idempotency-Key": idempotency_key
                },
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                job_info = response.json()
                self.job_id = job_info.get("job_id")
                print("📋 Response Body:")
                print(json.dumps(job_info, indent=2))
                print(f"\n✅ Job created: {self.job_id}")
                return True
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Job creation failed")
                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def get_job_info(self):
        """Get job information using GET /api/v1/jobs/{job_id}."""
        print("\n" + "="*60)
        print("📋 Job Status Check")
        print("="*60)

        print(f"📡 Endpoint: GET {self.base_url}/api/v1/jobs/{self.job_id}")
        print("📋 Headers:")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/jobs/{self.job_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code == 200:
                job_info = response.json()
                print("📋 Response Body:")
                print(json.dumps(job_info, indent=2))

                # Show stage summary
                stages = job_info.get("stages", [])
                print("\n📊 Stage Summary:")
                for stage in stages:
                    status_emoji = "✅" if stage.get("stage_state") == "COMPLETED" else "⏳" if stage.get("stage_state") == "PENDING" else "❌"
                    status_emoji = (
                        "✅" if stage.get("stage_state") == "COMPLETED"
                        else "⏳" if stage.get("stage_state") == "PENDING"
                        else "❌"
                    )

                return job_info
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Failed to get job info")
                return None

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return None

    def parse_catalog(self):
        """Parse the catalog file."""
        print("\n" + "="*60)
        print("📝 STEP 4: Parse Catalog")
        print("="*60)

        # Use the configured catalog file
        catalog_file = self.catalog_file

        if not catalog_file.exists():
            print(f"❌ Catalog file not found: {catalog_file}")
            return False

        print(f"ðŸ“ Catalog File: {catalog_file}")
        print(f"📊 File Size: {catalog_file.stat().st_size:,} bytes")

        print(f"\n📡 Endpoint: POST {self.base_url}/api/v1/jobs/{self.job_id}/stages/parse-catalog")
        print("📋 Headers:")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")
        print("📋 Files:")
        print(f"   file=@{catalog_file.name}")

        self.wait_for_enter("Press ENTER to parse catalog...")

        try:
            with open(catalog_file, 'rb') as f:
                files = {'file': (catalog_file.name, f, 'application/json')}
                response = requests.post(
                    f"{self.base_url}/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                    files=files,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=60,  # Longer timeout for file upload
                    verify=False
                )

                print(f"\n✅ Response Status: {response.status_code}")

                if response.status_code in [200, 201]:
                    result = response.json()
                    print("📋 Response Body:")
                    print(json.dumps(result, indent=2))
                    print("\n✅ Parse catalog successful!")

                    # Get job info after parse catalog
                    self.get_job_info()
                    return True
                else:
                    print("📋 Response Body:")
                    print(response.text)
                    print("\n❌ Parse catalog failed!")
                    return False

        except Exception as exc:
            print(f"\n❌ Error: {exc}")
            return False

    def generate_input_files(self):
        """Generate input files using the parsed catalog."""
        print("\n" + "="*60)
        print("⚙️  STEP 5: Generate Input Files")
        print("="*60)

        print(f"\n📡 Endpoint: POST {self.base_url}/api/v1/jobs/{self.job_id}/stages/generate-input-files")
        print("📋 Headers:")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")
        print("📋 Request Body: (empty, uses default adapter policy)")

        self.wait_for_enter("Press ENTER to generate input files...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                print("📋 Response Body:")
                print(json.dumps(result, indent=2))
                print("\n✅ Generate input files successful!")

                # Get job info after generate input files
                self.get_job_info()
                return True
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Generate input files failed")
                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def show_artifacts(self):
        """Show generated artifacts using tree command."""
        print("\n" + "="*60)
        print("📦 STEP 6: View Generated Artifacts")
        print("="*60)

        catalog_artifact_path = Path(self.build_stream_artifact_root) / "catalog"
        input_files_artifact_path = Path(self.build_stream_artifact_root) / "input-files"
        job_id_artifact_path = Path(self.build_stream_artifact_root) / self.job_id

        print(f"📂 Catalog artifacts: {catalog_artifact_path}")
        print(f"📂 Input files artifacts: {input_files_artifact_path}")
        print(f"📂 Job ID artifacts: {job_id_artifact_path}")

        self.wait_for_enter("Press ENTER to view artifacts...")

        # Show catalog artifacts
        if catalog_artifact_path.exists():
            print("\n📦 Catalog Artifacts:")
            try:
                result = subprocess.run(
                    ["tree", "-L", "2", "-h", str(catalog_artifact_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    self._fallback_artifact_list(catalog_artifact_path)
            except:
                self._fallback_artifact_list(catalog_artifact_path)
        else:
            print("\n❌ No catalog artifacts directory found")

        # Show input files artifacts
        if input_files_artifact_path.exists():
            print("\n📦 Input Files Artifacts:")
            try:
                result = subprocess.run(
                    ["tree", "-L", "2", "-h", str(input_files_artifact_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    self._fallback_artifact_list(input_files_artifact_path)
            except:
                self._fallback_artifact_list(input_files_artifact_path)
        else:
            print("\n❌ No input files artifacts directory found")

        # Show job ID artifacts
        if job_id_artifact_path.exists():
            print("\n📦 Job ID Artifacts:")
            try:
                result = subprocess.run(
                    ["tree", str(job_id_artifact_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    self._fallback_artifact_list(job_id_artifact_path)
            except:
                self._fallback_artifact_list(job_id_artifact_path)
        else:
            print(f"\n❌ Job ID artifacts directory not found: {job_id_artifact_path}")

        # Show content preview of the most recent artifacts
        self._show_latest_artifacts_preview(catalog_artifact_path, input_files_artifact_path)

    def _fallback_artifact_list(self, artifact_path):
        """Fallback method to list artifacts when tree command is not available."""
        artifacts = sorted(artifact_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        for artifact_dir in artifacts:
            if artifact_dir.is_dir():
                print(f"\n📦 {artifact_dir.name}/")
                for f in artifact_dir.iterdir():
                    size = f.stat().st_size
                    print(f"   📝 {f.name} ({size:,} bytes)")

    def _show_latest_artifacts_preview(self, catalog_path, input_files_path):
        """Show content preview of the most recent artifacts."""
        # Show latest catalog artifact
        if catalog_path.exists():
            catalog_artifacts = sorted(catalog_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            if catalog_artifacts:
                latest_catalog = catalog_artifacts[0]
                print(f"\n📋 Latest Catalog Artifact: {latest_catalog.name}")

                for f in latest_catalog.iterdir():
                    if f.name.endswith('.bin'):
                        print(f"\n📝 Content preview of {f.name}:")
                        try:
                            content = f.read_text()[:300]
                            print(content)
                            if len(f.read_text()) > 300:
                                print("...")
                        except:
                            print("   [binary data]")
                    elif f.name.endswith('.zip'):
                        print(f"\n📦 Archive contents of {f.name}:")
                        try:
                            result = subprocess.run(
                                ["unzip", "-l", str(f)],
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                print(result.stdout)
                        except:
                            print("   [unable to list archive contents]")

        # Show latest input files artifact
        if input_files_path.exists():
            input_artifacts = sorted(input_files_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            if input_artifacts:
                latest_input = input_artifacts[0]
                print(f"\n📋 Latest Input Files Artifact: {latest_input.name}")

                for f in latest_input.iterdir():
                    if f.name.endswith('.zip'):
                        print(f"\n📦 Archive contents of {f.name}:")
                        try:
                            result = subprocess.run(
                                ["unzip", "-l", str(f)],
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                print(result.stdout)
                        except:
                            print("   [unable to list archive contents]")

    def create_local_repository(self):
        """Create local repository using the generated input files."""
        print("\n" + "="*60)
        print("🏗️  STEP 7: Create Local Repository")
        print("="*60)

        print(f"\n📡 Endpoint: POST {self.base_url}/api/v1/jobs/{self.job_id}/stages/create-local-repository")
        print("📋 Headers:")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")
        print("📋 Request Body: (empty, uses job context from previous stages)")

        self.wait_for_enter("Press ENTER to create local repository...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs/{self.job_id}/stages/create-local-repository",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
                verify=False
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in [200, 201, 202]:
                result = response.json()
                print("📋 Response Body:")
                print(json.dumps(result, indent=2))
                print("\n✅ Create local repository successful!")

                # Get job info after create local repository
                self.get_job_info()
                return True
            else:
                print("📋 Response Body:")
                print(response.text)
                print("\n❌ Create local repository failed")
                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def _trigger_build_image_stage(self, step_label: str, architecture: str, functional_groups, inventory_host: str | None):
        print("\n" + "="*60)
        print(step_label)
        print("="*60)

        if not self.job_id:
            print("❌ No job_id available. Create a job before triggering this stage.")
            return False

        payload = {
            "architecture": architecture,
            "image_key": "demo-build-image",
            "functional_groups": functional_groups,
        }

        if inventory_host:
            payload["inventory_host"] = inventory_host

        print(f"📍 Endpoint: POST {self.base_url}/api/v1/jobs/{self.job_id}/stages/build-image")
        print("📋 Headers:")
        print(f"   Authorization: Bearer {self.access_token[:20]}...{self.access_token[-10:]}")
        print("📋 Request Body:")
        print(json.dumps(payload, indent=2))

        self.wait_for_enter("Press ENTER to trigger build-image stage...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs/{self.job_id}/stages/build-image",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=60,  # Longer timeout for build operations
                verify=False,
            )

            print(f"\n✅ Response Status: {response.status_code}")

            if response.status_code in (200, 202):
                print("📋 Response Body:")
                print(json.dumps(response.json(), indent=2))
                print("\n✅ Build image stage triggered!")
                return True

            print("📋 Response Body:")
            print(response.text)
            print("\n❌ Failed to trigger build image stage")
            return False

        except Exception as exc:
            print(f"\n❌ Error: {exc}")
            return False

    def trigger_build_image_x86_64_stage(self):
        """Trigger build image stage for x86_64 architecture."""
        groups = [
            "service_kube_control_plane_first_x86_64",
            "service_kube_control_plane_x86_64",
            "service_kube_node_x86_64",
            "slurm_control_node_x86_64",
            "slurm_node_x86_64",
            "login_node_x86_64",
            "login_compiler_node_x86_64",
        ]
        return self._trigger_build_image_stage(
            "🛠️  STEP 8A: Trigger Build Image Stage (x86_64)",
            "x86_64",
            groups,
            inventory_host=None,
        )

    def trigger_build_image_aarch64_stage(self):
        """Trigger build image stage for aarch64 architecture."""
        groups = [
            "slurm_node_aarch64",
            "login_node_aarch64",
            "login_compiler_node_aarch64",
        ]
        return self._trigger_build_image_stage(
            "🛠️  STEP 8B: Trigger Build Image Stage (aarch64)",
            "aarch64",
            groups,
            inventory_host="182.10.0.170",
        )

    def run_demo(self):
        """Run the complete demo."""
        print("\n" + "="*60)
        print("🚀 Parse-Catalog Interactive Demo")
        print("="*60)
        print("📋 This demo will execute the complete parse-catalog workflow")
        print("📋 using the real catalog_rhel.json file")
        print("  Press ENTER at each step to proceed")
        print("="*60)
        print(f"\n🔑 Demo Client ID: {self.client_id}")
        print(f"🔑 Correlation ID: {self.correlation_id}")

        try:
            # Cleanup artifacts if requested
            if self.cleanup:
                self.cleanup_artifacts()

            # Step 0: Health check
            if not self.check_server_health():
                return

            # Step 1: Register client (with retry loop)
            while True:
                # Step 1: Register client
                if not self.register_client():
                    return

                # Step 2: Get access token
                token_result = self.get_access_token()
                if token_result == True:
                    # Success, break the retry loop
                    break
                elif token_result == "retry_register":
                    # Ask user if they want to try registering again
                    while True:
                        user_input = input("\n❓ Do you want to try to register again? (yes/no): ").strip().lower()
                        if user_input in ['yes', 'y', 'no', 'n']:
                            break
                        print("   Please enter 'yes' or 'no'")

                    if user_input in ['yes', 'y']:
                        print("\n🔄 Attempting to register new client...")
                        # Clear existing credentials and continue the loop to retry
                        self.client_id = None
                        self.client_secret = None
                        continue
                    else:
                        print("\n⚠️  Continuing without valid credentials - demo cannot proceed.")
                        return
                else:
                    # Other failure, exit
                    return

            # Step 3: Create job
            if not self.create_job():
                return

            # Step 4: Parse catalog
            if not self.parse_catalog():
                return

            # Step 5: Generate input files
            if not self.generate_input_files():
                return

            # Step 6: Show artifacts
            self.show_artifacts()

            # Step 7: Create local repository
            if not self.create_local_repository():
                return

            # Step 8A: x86_64 build-image stage
            if not self.trigger_build_image_x86_64_stage():
                return

            # Step 8B: aarch64 build-image stage
            if not self.trigger_build_image_aarch64_stage():
                return

            print("\n" + "="*60)
            print("✅ Demo Completed Successfully!")
            print("="*60)
            print(f"📊 Client ID: {self.client_id}")
            print(f"📊 Job ID: {self.job_id}")
            print(f"📊 Correlation ID: {self.correlation_id}")
            print(f"📦 Catalog Artifacts: {Path(self.build_stream_artifact_root) / 'catalog'}/")
            print(f"📦 Input Files Artifacts: {Path(self.build_stream_artifact_root) / 'input-files'}/")
            print("📦 Local Repository: Created via Ansible playbook")
            print("📦 Build Image Stage: Submitted for both x86_64 and aarch64")
            print("="*60)

        except KeyboardInterrupt:
            print("\n\n⚠️ Demo interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Demo failed: {e}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Parse-Catalog Interactive Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Register a new client
    python buildstream_demo.py

    # Clean artifacts and register new client
    python buildstream_demo.py --cleanup
     """
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all contents in /opt/omnia/build_stream/artifacts before starting demo"
    )

    args = parser.parse_args()

    # Create and run demo
    demo = ParseCatalogDemo(cleanup=args.cleanup)
    demo.run_demo()


if __name__ == "__main__":
    main()
