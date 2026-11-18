# ragproof
A RAG pipeline is code without a compiler. Change the chunk size, swap the embedder, add a reranker — nothing fails, nothing warns. ragproof makes that change visible: it evaluates retrieval-augmented generation pipelines against a labelled set, compares variants on one leaderboard, and fails CI when retrieval quality regresses.  
