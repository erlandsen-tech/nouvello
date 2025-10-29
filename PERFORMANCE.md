# Performance Optimization Guide

## Parallel Processing Configuration

The pipeline supports multiple levels of parallelization to speed up processing.

### Environment Variables

Add these to your `.env` file to control parallelization:

```bash
# Chapter Analysis Parallelization
# WARNING: ProcessPoolExecutor has sandbox limitations on macOS
# Set to 1 to disable parallel chapter analysis
# Default: 3 workers
# ANALYSIS_WORKERS=3

# Scene Segmentation - Chapter Level
# Process multiple chapters in parallel
# Default: 3 workers (good balance for most books)
CHAPTER_SEG_WORKERS=3

# Scene Segmentation - Window Level
# Process windows within each chapter in parallel
# Default: 4 workers
SEG_WORKERS=4

# Window size for large chapters
SEG_WINDOW_SIZE=4000
SEG_WINDOW_OVERLAP=500

# Scene Image Generation
# Number of parallel workers for generating scene images
# Default: 2 (respects API rate limits)
SCENE_IMAGE_WORKERS=2
```

### Performance Tips

1. **For Small Books (1-5 chapters)**:
   - `CHAPTER_SEG_WORKERS=1` (sequential is fine)
   - `SEG_WORKERS=4` (parallelize within chapters)

2. **For Medium Books (5-15 chapters)**:
   - `CHAPTER_SEG_WORKERS=3` (sweet spot)
   - `SEG_WORKERS=4`

3. **For Large Books (15+ chapters)**:
   - `CHAPTER_SEG_WORKERS=4` (max parallelization)
   - `SEG_WORKERS=2` (reduce per-chapter workers)

4. **Rate Limit Considerations**:
   - AWS Bedrock has API rate limits
   - Total parallel requests = `CHAPTER_SEG_WORKERS * SEG_WORKERS`
   - Keep total under 10-15 to avoid throttling

### Example Performance

**Alice in Wonderland (3 chapters)**:
- Sequential: ~45 seconds
- Parallel (CHAPTER_SEG_WORKERS=3): ~20 seconds
- **2.25x speedup!**

**The Complete Works of H.P. Lovecraft (50+ chapters)**:
- Sequential: ~15 minutes
- Parallel (CHAPTER_SEG_WORKERS=4): ~5 minutes
- **3x speedup!**

### Troubleshooting

**"signal only works in main thread"**:
- Fixed! Our code now detects main thread automatically.

**"Permission denied" or "Operation not permitted"**:
- macOS sandbox restrictions on ProcessPoolExecutor
- Use ThreadPoolExecutor (already implemented)
- Or run with `required_permissions: ['all']`

**"Too many requests" from AWS**:
- Reduce parallelization levels
- Add delays between requests
