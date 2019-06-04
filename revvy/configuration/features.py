from revvy.configuration.version import Version


class FeatureMap:
    """Helper class to select a set of supported features for a given version"""
    def __init__(self, versions: dict):
        self._feature_map = {Version(v): features for v, features in versions.items()}

    def get_features(self, for_version: Version):
        max_version = None
        # get the greatest version that is <= for_version
        for version in self._feature_map:
            if for_version >= version:
                if max_version is None or version > max_version:
                    max_version = version
        if max_version is None:
            raise ValueError("Can't find feature map for version {}".format(for_version))
        else:
            print('Returning features for version {}'.format(max_version))
        return self._feature_map[max_version]
