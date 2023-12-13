from typing import Dict, List, Annotated
import numpy as np
import faiss
from memory_profiler import profile


class VecDB_ivf_pq:
    def __init__(self, file_path="saved_db.csv", new_db=True) -> None:
        self.file_path = file_path
        self.d = 70  # vector dimensions
        if new_db:
            # just open new file to delete the old one
            with open(self.file_path, "w") as fout:
                # if you need to add any head to the file
                pass

    def insert_records(self, rows: List[Dict[int, Annotated[List[float], 70]]]):
        # rows is a list of dictionary, each dictionary is a record
        with open(self.file_path, "a+") as fout:
            # TODO: keep track of the last id in the database,
            # to start the new index from it, if the database is not empty,
            # and if the index algorithm requires it
            for row in rows:
                # get id and embed from dictionary
                id, embed = row["id"], row["embed"]
                # convert row to string to write it to the database file
                # TODO: Convert str(e) to bytes to reduce the size of the file
                # float should be 4 bytes, but str(e) is more than that
                # TODO: try to take info from the embed, so you can use it to build the index
                row_str = f"{id}," + ",".join([str(e) for e in embed])
                fout.write(f"{row_str}\n")
        # build index after inserting all records,
        # whether on new records only or on the whole database
        self._build_index()

    # Worst case implementation for retrieve
    # Because it is sequential search
    @profile
    def retrive(self, query: Annotated[List[float], 70], top_k=5):
        # TODO: for our implementation, we will use the index to retrieve the top_k records
        # then retrieve the actual records from the database
        scores = []
        loaded_index = faiss.read_index(f"./index/ivf_pq.index")

        distances, labels = loaded_index.search(query, top_k)

        scores = [(distances[0][i], labels[0][i]) for i in range(len(labels[0]))]
        scores = sorted(scores, reverse=True)[:top_k]
        # print(scores)
        # return the ids of the top_k records
        return [s[1] for s in scores]

    def _cal_score(self, vec1, vec2):
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        cosine_similarity = dot_product / (norm_vec1 * norm_vec2)
        return cosine_similarity

    def _build_index(self):
        # TODO: build index for the database
        print("Building index...")
        bucket_rec = []
        with open(self.file_path, "r") as fin:
            # search through the file line by line (sequentially)
            # each row is a record
            for row in fin.readlines():
                row_splits = row.split(",")
                # the first element is id
                id = int(row_splits[0])
                # the rest are embed
                embed = [float(e) for e in row_splits[1:]]
                embed = np.array(embed)
                bucket_rec.append((id, embed))
        self._ivf_pq_index(
            data=bucket_rec,
        )

    def _ivf_pq_index(self, data):
        # Create an index with ID support
        index = faiss.index_factory(self.d, "IVF256,PQ70x8")
        # index = faiss.index_factory(self.d, "IVF256_HNSW,PQ35")
        xb = np.array([x[1] for x in data])
        ids = np.array([x[0] for x in data])

        # Train the index with xb
        index.train(xb)

        # Create an IndexIDMap around the base index
        index = faiss.IndexIDMap(index)

        # Assuming ids is a 1-D numpy array that contains the IDs of your vectors in xb
        index.add_with_ids(xb, ids)

        faiss.write_index(index, f"./index/ivf_pq.index")
