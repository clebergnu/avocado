from avocado.utils.asset import AssetSpec
from avocado.utils.asset import pipe_runner
from avocado.utils.asset import XZUncompressRetriever

pipe_runner(AssetSpec('https://avocado-project.org/data/assets/jeos-23-64.qcow2.xz',
                      expected='79f4a565a91fbb485430efd476f66e7ed409366d'),
            AssetSpec('jeos-23-64.qcow2',
                      expected='bef082caf04021c8de8543e3423b2fdc5ecb94da',
                      retriever=XZUncompressRetriever))
