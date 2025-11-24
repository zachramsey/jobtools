Job Search
---
A job post aggregator so I can stop wasting time on job sites.

### Keyword Optimization

**1. Create embeddings of job postings with Sentence-BERT (SBERT)**
- purpose-built for semantic comparison
- `sentence-transformers` library
- Fast and lightweight: `all-MiniLM-L6-v2`
- Best all-around model: `all-mpnet-base-v2`

**2. Cluster embedded job postings with HDBSCAN**
- Automatically determines the optimal number of clusters from the data's structure
- Can detect and filter out unique, rare, or poorly defined job postings
- Can find clusters that are dense and compact as well as those that are more sparse

**3. Profile clusters and provide human-readable labels**
- Take centroid postings of each cluster as representatives
- Manual approach: Just look at prototypical postings and manually label
- Automatic approach: Feed prototypical postings into a summarization model (like BART or T5)

**4. Extract Distinguishing Keywords with c-TF-IDF**
- Term Frequency (TF): Frequency of each word in each cluster.
- Inverse Document Frequency (IDF): Inverse of number of clusters in which each word appears.
- c-TF-IDF Score: Product of TF & IDF for a word in a cluster.
- Higher c-TF-IDF score indicates a word is more unique to that cluster.

**5. Build queries with semantic sub-clustering of keywords**
- Take top M keyword from c-TF-IDF and retrieve word embeddings with Word2Vec
- Sub-cluster keyword embeddings with an algorithm like Agglomerative Hierarchical Clustering
- *Potentially some minimum c-TF-IDF score cutoff for inclusion*
- Join keywords within each cluster with `OR` and join each sub-cluster with `AND`

