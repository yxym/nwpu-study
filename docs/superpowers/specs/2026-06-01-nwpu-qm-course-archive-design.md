# NWPU QM Course Archive Design

## Purpose

Build this repository into a public course-material archive for NWPU Queen Mary Engineering School, inspired by `PKUanonym/REKCARC-TSC-UHT`, while avoiding accidental publication of private or unrelated files from the local `大学` folder.

The archive should cover these semesters:

- `大一上`
- `大一下`
- `大二上`
- `大二下`
- `大三上`

The guiding rule is whitelist-first publication: only explicitly approved semester/course folders are candidates for import. Everything else is private or out of scope by default.

## Source And Target

Source root:

```text
/Users/chexuanming/Desktop/大学
```

Target repository:

```text
/Users/chexuanming/Desktop/nwpu-study
```

The target repository already contains some course folders under `大一下` and `大二下`. The redesign should preserve useful existing material, add missing public semesters/courses, and improve documentation and review workflow.

## Public File Policy

### Include

The user approved including:

- personal coursework
- lab reports
- raw data
- files containing the user's name, student ID, or group information
- textbooks and ebooks
- teacher-provided answers
- the user's notes, summaries, review material, code, posters, presentations, and course outputs

### Exclude

The user requested excluding:

- courseware and lecture slides
- senior-student materials
- previous-year materials

The workflow should also exclude or flag non-course/private material by default, including student-union work, class rosters, signup forms, resumes, party-application files, outbound-study files, competition administration, and other unrelated personal folders.

### Ambiguous Items

Some filenames are ambiguous, especially PDFs named like chapters, weeks, module guides, translated lecture notes, or revision sheets. The import workflow should not rely on automatic deletion for these. It should generate a review list that marks ambiguous files for human confirmation before import.

## Repository Structure

Use a simple semester-to-course hierarchy:

```text
README.md
收录内容.md
贡献方法.md
LICENSE
public-whitelist.yml
docs/
  public-file-policy.md
  review/
    candidates.md
scripts/
  collect_candidates.py
  sync_public_files.py
  build_manifest.py
大一上/
  课程名/
大一下/
  课程名/
大二上/
  课程名/
大二下/
  课程名/
大三上/
  课程名/
```

Course directories should keep original filenames where possible. The workflow may remove obvious local junk such as `.DS_Store`, Office lock files, temporary files, and duplicate archive artifacts when they are not the primary source.

## Whitelist Configuration

Create `public-whitelist.yml` to explicitly list approved source course folders and target course names. The first version should include the five approved semesters and course directories identified from the local folder structure, but no files should be imported until the generated candidate list is reviewed.

The whitelist should support:

- source path relative to `/Users/chexuanming/Desktop/大学`
- target semester
- target course name
- optional aliases for duplicate folders, such as `高物` and `2025高分子物理`
- optional per-course include/exclude overrides

## Candidate Generation

`scripts/collect_candidates.py` should scan only the whitelist entries and write `docs/review/candidates.md`.

Each candidate file should be categorized as:

- `建议收录`: likely public under the approved policy
- `建议排除`: likely courseware, senior-student material, previous-year material, private/non-course material, local junk, or generated duplicate
- `需要人工判断`: unclear from filename alone

The candidate report should group files by semester and course. It should show each file's source path, target path, size, file type, and reason for the category.

## Import Workflow

`scripts/sync_public_files.py` should copy only files approved by the reviewed candidate list. It should never scan or import from folders that are not in `public-whitelist.yml`.

The script should:

- create missing target semester/course directories
- preserve source filenames unless a collision requires a deterministic suffix
- skip `.DS_Store`, temporary files, Office lock files, and other local artifacts
- avoid copying excluded candidates
- write a machine-readable manifest of imported files
- support a dry-run mode before copying

The import should happen after candidate review, not during the design/spec phase.

## Documentation

Update or create:

- `README.md`: project introduction, source inspiration, usage, Git LFS note, public boundary, and academic-integrity warning
- `收录内容.md`: semester/course index and summarized material types
- `贡献方法.md`: contribution rules, naming suggestions, privacy policy, and excluded material policy
- `docs/public-file-policy.md`: detailed include/exclude rules and examples

The tone should be similar to public course-resource repositories: helpful, explicit about boundaries, and clear that materials are for reference only.

## Git And Large Files

The repository currently uses Git LFS for `xlsx`, `zip`, `pptx`, and `docx`, and `git status` can fail when the LFS clean filter tries to write under `.git/lfs/tmp`. The implementation should handle this before major imports.

Minimum required behavior:

- keep large binary/course files under Git LFS where appropriate
- make normal status checks usable, either by fixing the LFS temp issue or by documenting the safe status command for this repository
- avoid adding files larger than GitHub's normal file limit outside LFS
- avoid committing generated review artifacts that expose excluded private paths unless the user approves their contents

## Verification

Before reporting implementation complete, run checks that verify:

- every imported file is under a whitelisted semester/course
- excluded directory keywords are absent from imported paths
- obvious courseware keywords are absent unless the file was explicitly approved
- `.DS_Store`, Office lock files, and temporary files are not imported
- generated indexes match the final repository tree
- Git LFS tracking covers configured binary file types

Manual review remains required for final publication because filename-based filtering cannot prove a file's privacy, copyright, or suitability.

## Out Of Scope

This design does not publish the repository, push to GitHub, or make final decisions about ambiguous files. It also does not rewrite file contents, redact documents, or inspect private document bodies unless the user explicitly asks for that later.

## Approved Design Choices

The user approved:

- using a whitelist rather than a blacklist
- covering all five public semesters from `大一上` through `大三上`
- excluding courseware
- allowing personal coursework, reports, raw data, and files containing name/student ID/group information
- allowing textbooks, ebooks, and teacher-provided answers
- excluding senior-student and previous-year materials
- using a candidate-review step before actual import
