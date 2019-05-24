import os
import json
import hashlib


class IntegrityError(Exception):
    pass


class StorageInterface:
    def read_metadata(self, filename):
        raise NotImplementedError

    def write(self, filename, data, md5=None):
        raise NotImplementedError

    def read(self, filename):
        raise NotImplementedError


class FileStorage(StorageInterface):
    """
    Stores files on disk, under the storage_dir directory.

    Stores 2 files for each stored file:
      x.meta: stores md5 and length in json format for the data
      x.data: stores the actual data
    """

    def __init__(self, storage_dir):
        self._storage_dir = storage_dir
        try:
            os.makedirs(self._storage_dir, 0o755, True)
            with open(self.access_file(), "wb") as fp:
                fp.write(b"true")
        except IOError as err:
            print("Invalid storage directory set. Not writable.")
            print(err)
            raise

    def access_file(self):
        return os.path.join(self._storage_dir, "access-test")

    def storage_file(self, filename):
        return os.path.join(self._storage_dir, "{}.data".format(filename))

    def meta_file(self, filename):
        return os.path.join(self._storage_dir, "{}.meta".format(filename))

    def read_metadata(self, filename):
        with open(self.meta_file(filename), "rb") as meta_file:
            return json.loads(meta_file.read().decode("utf-8"))

    def write(self, filename, data, md5=None):
        if md5 is None:
            md5 = hashlib.md5(data).hexdigest()

        with open(self.storage_file(filename), "wb") as data_file, open(self.meta_file(filename), "wb") as meta_file:
            metadata = {
                "md5":    md5,
                "length": len(data)
            }
            data_file.write(data)
            meta_file.write(json.dumps(metadata).encode("utf-8"))

    def read(self, filename):
        with open(self.storage_file(filename), "rb") as data_file, open(self.meta_file(filename), "rb") as meta_file:
            metadata = json.loads(meta_file.read().decode("utf-8"))
            data = data_file.read()
            if len(data) != metadata['length'] or hashlib.md5(data).hexdigest != metadata['md5']:
                raise IntegrityError
            return data
