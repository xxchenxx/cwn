import torch
import os.path as osp

from data.datasets import InMemoryComplexDataset
from data.datasets.ring_utils import generate_ringlookup_graph_dataset
from data.utils import convert_graph_dataset_with_rings


class RingLookupDataset(InMemoryComplexDataset):

    def __init__(self, root, nodes=10):
        self.name = 'RING-LOOKUP'
        self._nodes = nodes

        super(RingLookupDataset, self).__init__(
            root, None, None, None, max_dim=2, cellular=True, num_classes=nodes-1)

        self.data, self.slices = torch.load(self.processed_paths[0])
        idx = torch.load(self.processed_paths[1])

        self.train_ids = idx[0]
        self.val_ids = idx[1]
        self.test_ids = idx[2]

    @property
    def processed_dir(self):
        """This is overwritten, so the simplicial complex data is placed in another folder"""
        return osp.join(self.root, 'complex')

    @property
    def processed_file_names(self):
        return [f'ringlookup-n{self._nodes}.pkl', f'idx-n{self._nodes}.pkl']

    @property
    def raw_file_names(self):
        # No raw files, but must be implemented
        return []

    def download(self):
        # Nothing to download, but must be implemented
        pass

    def process(self):
        train = generate_ringlookup_graph_dataset(self._nodes, samples=10000)
        val = generate_ringlookup_graph_dataset(self._nodes, samples=1000)
        dataset = train + val

        train_ids = list(range(len(train)))
        val_ids = list(range(len(train), len(train) + len(val)))
        print("Converting dataset to a cell complex...")

        complexes, _, _ = convert_graph_dataset_with_rings(
            dataset,
            max_ring_size=self._nodes,
            include_down_adj=False,
            init_edges=True,
            init_rings=True,
            n_jobs=4)

        for complex in complexes:
            # Add mask for the target node.
            mask = torch.zeros(complex.nodes.num_simplices, dtype=torch.bool)
            mask[0] = 1
            setattr(complex.chains[0], 'mask', mask)

            # Make HOF zero
            complex.edges.x = torch.zeros_like(complex.edges.x)
            complex.triangles.x = torch.zeros_like(complex.triangles.x)
            assert complex.triangles.num_simplices == 1

        path = self.processed_paths[0]
        print(f'Saving processed dataset in {path}....')
        torch.save(self.collate(complexes, 2), path)

        idx = [train_ids, val_ids, None]

        path = self.processed_paths[1]
        print(f'Saving idx in {path}....')
        torch.save(idx, path)


def load_ring_lookup_dataset(nodes=10):
    train = generate_ringlookup_graph_dataset(nodes, samples=10000)
    val = generate_ringlookup_graph_dataset(nodes, samples=1000)
    dataset = train + val

    train_ids = list(range(len(train)))
    val_ids = list(range(len(train), len(train) + len(val)))

    return dataset, train_ids, val_ids, None
