# Reproducibility

Core source/tests are reproducible from the lock only after platform portability is repaired. The
historical full corpus and benchmark output are ignored and absent from this checkout, so published
numbers cannot be exactly reproduced from Git alone.

Every future result manifest must record: code commit; evaluation-set SHA-256; corpus manifest and
chunk-file SHA-256; source list/version hashes; lock SHA-256; Python/OS/hardware; configuration and
local service versions; command; start/end time; output hashes; failures; and reviewer/adjudication
artifact references. Mutable current-site reruns must receive new identities.

Do not commit full corpus, private review material, transcripts, audit logs, model weights, or Qdrant
state merely to make a claim reproducible. Prefer lawful source/hash manifests and independently
generated local artifacts.
