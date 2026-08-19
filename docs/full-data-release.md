# Row-level data release

Release `public-m12` contains all 442,211,685 accepted analytical rows in Parquet:

- one generalized member row per subscriber;
- every accepted subscription transaction;
- both observed churn-label windows;
- every accepted subscriber-day listening row.

Subscriber and event keys are re-generated as collision-checked 64-bit one-way pseudonyms for this release and cannot be joined to private product tokens. Source identifiers are absent. Exact reported age becomes a 10-year band, and exact member registration date becomes registration month.

The [public dataset](https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence) contains 32 files and 7,522,254,856 compressed bytes. Its four Viewer configurations separate members, subscription transactions, churn labels, and listening days. The manifest lists every object, grain, row count, and byte size. Files use Zstandard compression and preserve typed dates, amounts, event flags, listening counts, and quality flags.

The release uses public Hugging Face dataset storage and adds no recurring infrastructure cost. GitHub contains build, verification, product, and contract code only; it does not contain the dataset or publication salt.

This is a historical consumer-subscription dataset. Payment fields are gross receipts in source currency, not recognized revenue. Churn labels are observed challenge outcomes, not treatment effects.
