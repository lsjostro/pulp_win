#!/usr/bin/python

import os
import requests
from requests.exceptions import HTTPError
import hashlib
import json
from optparse import OptionParser
from glob import glob
from msilib import *

CHUNK_SIZE = 1048576 # 1 Mb chunk size

class MsiUploader():
    def __init__(self, url, user, password):
        self.base_url = url
        self.basic_auth = (user, password)

    def get_repo(self, repo_id):
        repo_path = "/pulp/api/v2/repositories/%s/" % repo_id
        r = requests.get(self.base_url + repo_path, auth=self.basic_auth, verify=False)
        if r.status_code == 404:
            return False
        return True

    def create_repo(self, repo_id):
        repo_base = "/pulp/api/v2/repositories/"
        importer_path = repo_base + "%s/importers/" % repo_id
        distributor_path = repo_base + "%s/distributors/" % repo_id

        repo_metadata = {
            "display_name": "MSI repo: %s" % repo_id,
            "id": repo_id,
            "notes": { "_repo-type" : "win-repo" }
        }

        r = requests.post(self.base_url + repo_base, auth=self.basic_auth, verify=False, data=json.dumps(repo_metadata))
        r.raise_for_status()

        importer_data = {
            "importer_type_id": "win_importer",
            "importer_config": {}
        }
        distributor_data = {
            "distributor_type_id": "win_distributor",
            "distributor_config": { "http" : True, "https" : False, "relative_url" : repo_id },
            "auto_publish": True
        }

        r = requests.post(self.base_url + importer_path, auth=self.basic_auth, verify=False, data=json.dumps(importer_data))
        r.raise_for_status()

        r = requests.post(self.base_url + distributor_path, auth=self.basic_auth, verify=False, data=json.dumps(distributor_data))
        r.raise_for_status()

    def upload_file(self, filename, repo_id):
        repo_path = "/pulp/api/v2/repositories/%s/" % repo_id
        upload_req_path = "/pulp/api/v2/content/uploads/"
        import_path = repo_path + "actions/import_upload/"

        name = self._get_msi_property(filename, "ProductName")
        version = self._get_msi_property(filename, "ProductVersion")

        r = requests.post(self.base_url + upload_req_path, auth=self.basic_auth, verify=False)
        r.raise_for_status()
        upload_id = r.json()['upload_id']

        try:
            file_size = os.path.getsize(filename)
            offset = 0

            m = hashlib.new('md5')
            f = open(filename, 'rb')
            while True:
                # Load the chunk to upload
                f.seek(offset)
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                # calc md5
                m.update(data)
                # Server request
                upload_path = "/pulp/api/v2/content/uploads/%s/%s/" % (upload_id, offset)
                r = requests.put(self.base_url + upload_path, auth=self.basic_auth, verify=False, data=data)
                r.raise_for_status()

                offset = min(offset + CHUNK_SIZE, file_size)
            f.close()
            unit_metadata = {
                "upload_id": upload_id,
                "unit_type_id": "msi",
                "unit_key": { "name": name, "checksum": m.hexdigest(), "version": version, "checksumtype": "md5" },
                "unit_metadata": { "filename": os.path.basename(filename) }
            }
            # Post metadata for unit
            r = requests.post(self.base_url + import_path, auth=self.basic_auth, verify=False, data=json.dumps(unit_metadata))
            r.raise_for_status()

        except (HTTPError, IOError), e:
            raise

        finally:
            delete_path = "/pulp/api/v2/content/uploads/%s/" % upload_id
            r = requests.delete(self.base_url + delete_path, auth=self.basic_auth, verify=False)
            r.raise_for_status()

        return True

    def publish_repo(self, repo_id):
        repo_path = "/pulp/api/v2/repositories/%s/" % repo_id
        publish_path = repo_path + "actions/publish/"
        distributor_data = {
            "id": "win_distributor",
            "override_config": {}
        }
        r = requests.post(self.base_url + publish_path, auth=self.basic_auth, verify=False, data=json.dumps(distributor_data))
        r.raise_for_status()
        return True

    def _get_msi_property(self, path, prop):
        try:
            db = OpenDatabase(path, MSIDBOPEN_READONLY)
        except:
            raise
        view = db.OpenView ("SELECT Value FROM Property WHERE Property='%s'" % prop)
        view.Execute(None)
        result = view.Fetch()
        return result.GetString(1)

def parse_options():
    parser = OptionParser()

    parser.add_option('-f', '--file', type="string", dest="filename",
                     help="msi file")
    parser.add_option('-u', '--username', type="string", dest="username",
                     help="Username")
    parser.add_option('-p', '--password', type="string", dest="password",
                     help="Password")
    parser.add_option('-b', '--base-url', type="string", dest="base_url",
                     help="Base URL to Pulp server")
    parser.add_option('-r', '--repo-id', type="string", dest="repo_id",
                     help="Repo ID")
    options, args = parser.parse_args()

    if (not options.filename or not options.repo_id or not options.base_url
        or not options.username or not options.password):
        parser.error("use --help for help ")

    return options

def main():
    options = parse_options()

    filename = glob(options.filename)
    if not filename:
        raise OSError("File not found")

    m = MsiUploader(options.base_url, options.username, options.password)

    ## Check if repo exists else create it.
    if not m.get_repo(options.repo_id):
        m.create_repo(options.repo_id)
    ## Upload file
    m.upload_file(filename[0], options.repo_id)
    ## Publish unit
    m.publish_repo(options.repo_id)

    print "Upload complete!"

if __name__ == '__main__':
    main()
