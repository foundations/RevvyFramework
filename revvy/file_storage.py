import os
import json
import hashlib
from json import JSONDecodeError


class StorageError(Exception):
    pass


class StorageElementNotFoundError(StorageError):
    pass


class IntegrityError(StorageError):
    pass


class StorageInterface:
    def read_metadata(self, filename):
        raise NotImplementedError

    def write(self, filename, data, md5=None):
        raise NotImplementedError

    def read(self, filename):
        raise NotImplementedError


class MemoryStorage(StorageInterface):
    def __init__(self):
        self._entries = {}

    def read_metadata(self, name):
        if name not in self._entries:
            raise StorageElementNotFoundError

        return {'md5': self._entries[name][0], 'length': len(self._entries[name][1])}

    def write(self, name, data, md5=None):
        if md5 is None:
            md5 = hashlib.md5(data).hexdigest()

        self._entries[name] = (md5, data)

    def read(self, name):
        metadata = self.read_metadata(name)
        data = self._entries[name][1]

        if hashlib.md5(data).hexdigest() != metadata['md5']:
            raise IntegrityError('Checksum')
        return data


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
            with open(self._access_file(), "w") as fp:
                fp.write("true")
        except IOError as err:
            print("Invalid storage directory set. Not writable.")
            print(err)
            raise

    def _path(self, filename):
        return os.path.join(self._storage_dir, filename)

    def _access_file(self):
        return self._path("access-test")

    def _storage_file(self, filename):
        return self._path("{}.data".format(filename))

    def _meta_file(self, filename):
        return self._path("{}.meta".format(filename))

    def read_metadata(self, filename):
        try:
            with open(self._meta_file(filename), "r") as meta_file:
                return json.loads(meta_file.read())
        except IOError:
            raise StorageElementNotFoundError

    def write(self, filename, data, md5=None):
        if md5 is None:
            md5 = hashlib.md5(data).hexdigest()

        with open(self._storage_file(filename), "wb") as data_file, open(self._meta_file(filename), "w") as meta_file:
            metadata = {
                "md5":    md5,
                "length": len(data)
            }
            data_file.write(data)
            json.dump(metadata, meta_file)

    def read(self, filename):
        try:
            data_file_path = self._storage_file(filename)
            meta_file_path = self._meta_file(filename)
            with open(data_file_path, "rb") as data_file, open(meta_file_path, "r") as meta_file:
                metadata = json.load(meta_file)
                data = data_file.read()
                if len(data) != metadata['length']:
                    raise IntegrityError('Length')
                if hashlib.md5(data).hexdigest() != metadata['md5']:
                    raise IntegrityError('Checksum')
                return data
        except IOError:
            raise StorageElementNotFoundError
        except JSONDecodeError:
            raise IntegrityError('Metadata')
