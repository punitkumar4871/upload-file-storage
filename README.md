# Distributed File Upload Recovery & Auto Merge System

A scalable automated file reconstruction system that detects uploaded file chunks, validates upload completeness, merges files back into their original format, and automates recovery workflows using GitHub Actions.

The system is designed for handling large distributed uploads where files are split into multiple parts and uploaded independently.

---

## Features

- Automatic upload scanning
- Chunk detection and validation
- File integrity verification
- Automatic file reconstruction
- SHA256 checksum generation
- Re-upload detection
- Retry mechanism for failed Git operations
- GitHub Actions automation
- Artifact generation for merged files
- Prevent duplicate merges
- Supports interrupted upload recovery

---

## System Workflow

```

Large File Upload
|
v

Split into Parts

```
video.part1of10
video.part2of10
video.part3of10
...
```

|
v

Uploads Directory

```
uploads/
```

|
v

Scan Uploads

```
scan_uploads.py
```

|
v

Validation Pipeline

```
validate.py
```

|
v

Merge Engine

```
merge.py
```

|
v

SHA256 Verification

```
filename.sha256
```

|
v

Merged Output

```
merged/uploads/YYYY/MM/DD/
```

|
v

GitHub Artifact Upload

|
v

Download Final File

---

## Project Structure

```

project/

├── scripts/
│
├── scan_uploads.py
├── merge.py
├── git_service_patch.py
│
├── .github/
│ └── workflows/
│ └── auto-merge.yml
│
├── uploads/
│ └── uploaded chunks
│
├── merged/
│ └── reconstructed files
│
└── README.md

```

---

## Core Components

### scan_uploads.py

Responsible for:

- Scanning upload folders
- Detecting completed uploads
- Checking missing chunks
- Preventing duplicate merges
- Detecting re-uploaded parts
- Generating merge queue

Example:

```

movie.part1of5.mp4
movie.part2of5.mp4
movie.part3of5.mp4
movie.part4of5.mp4
movie.part5of5.mp4

```

When all parts exist:

```

READY FOR MERGE

```

---

### merge.py

Responsible for:

- Sorting file chunks correctly
- Preventing ordering bugs
- Merging chunks sequentially
- Computing SHA256 checksums
- Removing stale merged files
- Supporting re-merge operations

Example:

```

part1
part2
part3

↓

original_file.mp4

```

Generated:

```

merged/video.mp4
merged/video.mp4.sha256

```

---

### git_service_patch.py

Improves Git upload reliability.

Features:

- Retry failed commits
- Handle transient HTTP failures

Supports:

```

429 Too Many Requests
500 Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout

```

Retry strategy:

```

Attempt 1 → Wait 2s
Attempt 2 → Wait 5s
Attempt 3 → Wait 10s
Attempt 4 → Wait 20s
Attempt 5 → Wait 30s

```

Manifest files are uploaded only after all file parts succeed.

---

### GitHub Actions Workflow

Workflow file:

```

auto-merge.yml

```

Pipeline:

### Job 1 — Detect Uploads

Checks:

- Complete file groups
- Upload completion status

### Job 2 — Validate Files

Checks:

- Missing chunks
- File corruption
- Integrity validation

### Job 3 — Merge Files

Actions:

- Merge file chunks
- Generate SHA256
- Upload merged files as artifacts
- Store checksums
- Generate workflow summary

---

## Merge Logic

Example:

Input:

```

report.part1of3.pdf
report.part2of3.pdf
report.part3of3.pdf

```

Output:

```

merged/report.pdf

```

Checksum:

```

report.pdf.sha256

```

---

## Duplicate Prevention

The system avoids unnecessary merges.

Logic:

```

Checksum exists
AND

No newer chunk uploaded

↓

Skip merge

```

If newer chunks are uploaded:

```

Re-upload detected

↓

Force re-merge

```

---

## Output Directory

```

merged/

└── uploads/

└── YYYY/

└── MM/

└── DD/

└── final_file.ext

```

---

## Integrity Verification

SHA256 checksum generation ensures:

- Data consistency
- Corruption prevention
- Merge verification

Example:

```

SHA256:

d2f5a0e7e8c5...

```

---

## Technologies Used

- Python 3
- GitHub Actions
- SHA256 Hashing
- File System Operations
- Upload Chunk Management
- CI/CD Automation

---

## Future Improvements

- Parallel merge processing
- Database metadata tracking
- Upload dashboard
- Retry upload API
- Distributed object storage
- Compression optimization
- Chunk encryption

---

## Author

Punit Kumar

Automated Distributed File Recovery & Merge Pipeline
