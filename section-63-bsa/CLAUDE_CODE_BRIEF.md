# BSA Section 63 Certificate Platform — Brief for Claude Code

> **How to use this file:** put it in an empty project folder, open Claude Code there and say:
> *"Read CLAUDE_CODE_BRIEF.md and build Phase 1 exactly as specified. Use the statutory text in Section 2.3 word for word. Ask me before deviating from it."*

Proof-of-concept web app: users add electronic evidence, the app extracts technical metadata, computes hashes, and drafts the certificate in the format prescribed by the **Schedule to Section 63(4)(c) of the Bharatiya Sakshya Adhiniyam, 2023 (BSA, Act 47 of 2023)**.

> ⚠️ **Verify before production:** the statutory wording in Section 2 is reproduced from the BSA bare Act. Check punctuation and layout against the official India Code PDF (link in Sources) before going live. If the official text and any website differ, **the official text wins.**

---

## 1. Your request vs my suggestion vs what you want

| # | Your original request | My suggestion | What you want (build requirement for Claude Code) |
|---|---|---|---|
| 1 | An interface to upload pictures, recordings, WhatsApp messages and other evidence. | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui, with a drag-and-drop uploader. | A responsive web app that accepts images, audio, video, PDFs/documents, WhatsApp chat exports (`.txt` or `.zip` with media) and any other file as generic evidence. |
| 2 | Generate certificates under Section 63 BSA. | Generate a PDF that reproduces the **Schedule word for word**: Part A (Party) and Part B (Expert), plus the hash report annexure the Schedule asks for. | A certificate wizard that pre-fills the technical fields (hashes, file details, device metadata) and outputs a **draft** PDF in the exact Schedule format. Signature boxes stay blank so the people concerned can sign. |
| 3 | *(implied by the certificate)* Hash values. | SHA-256 as the default. Also compute MD5 and SHA-1 because the Schedule lists all three. In the MVP, hash in the browser so files are never uploaded. | Compute and store SHA-256, SHA-1 and MD5 for every file, in the browser. Generate the hash report annexure. Let the user re-verify a file later and compare with an acquisition hash they type in. |
| 4 | Track user logs. | **MVP:** an append-only, hash-chained audit log stored in the browser (IndexedDB) that can be exported. **Phase 2:** a server-side log in Supabase. | Log evidence creation, file hashing, re-verification, edits, certificate generation and finalising, downloads and bundle export/import, with IST timestamp and user agent. Include a "Verify chain" check. |
| 5 | Possibly a login page. **Update: leave it out of the MVP and add it later.** | No login in Phase 1. Add Supabase Auth (email + password) with Row Level Security in Phase 2. | **No login in the MVP.** The app works straight away in the browser, and data stays on the user's device. The data model is ready for user accounts and cloud sync in Phase 2 (Appendix A). |
| 6 | Possibly payment per certificate. | Design for Razorpay later. Not part of the MVP. | Payments are an optional future module. Leave room in the data model, but write no payment code in Phase 1. |
| 7 | Build a proof of concept first. | A **static, browser-only** Next.js app with no backend: no Supabase and no microservices in Phase 1. | A working MVP: add files → hash → metadata → certificate draft → history, all in the browser, with export and import of a case bundle as a backup. |
| 8 | Possibly commercialise later. | Keep evidence processing, legal templates and billing in separate modules. | Modular code (`lib/evidence`, `lib/legal`, `lib/billing`) so it can grow into a SaaS. |
| 9 | — *(added in my suggestion)* | Build around an **Evidence** record, not a Certificate record. | `Evidence` is the central entity. Files, devices, hash reports, certificate versions and audit events all belong to it. |
| 10 | — *(added in my suggestion)* | The app **drafts**. It cannot certify. | Clear disclaimers. The Section 63(2) declarations are made by the party, and Part B is signed by an expert. The app only pre-fills technical facts and stamps the PDF "DRAFT". |
| 11 | — *(added in my suggestion)* | Section 63(4) requires a certificate "at each instance" the record is submitted. | Certificates are versioned for each submission, with court and case number recorded. |
| 12 | Host it on GitHub Pages or AWS. | GitHub Pages for the MVP (free, auto-deploys). AWS Amplify when you need AWS or Phase 2 server features. S3 + CloudFront for the lowest cost. | Build as a static export (`output: 'export'`) that runs on any of the three. Include the GitHub Pages deploy workflow. Step-by-step instructions are in Section 4. |

---

## 2. What the bare Act requires (reference for the build)

### 2.1 Section 63: provisions mapped to features

| Provision | What it says | What the app does |
|---|---|---|
| **63(1)** | Information in an electronic record that is printed, stored, recorded or copied ("computer output") is deemed a document. It is admissible without producing the original **if the conditions in this section are met**. | This is the app's purpose: help prepare the certificate that goes with computer output (printouts, copies, exports). |
| **63(2)(a)** | The output was produced while the computer or communication device was **regularly used** for an activity carried on by the person **having lawful control** over it. | Covered by the Part A declaration text, which the party must affirm. The app cannot verify this. |
| **63(2)(b)** | Information of that kind was **regularly fed** into the device in the ordinary course of those activities. | Same as 63(2)(a). |
| **63(2)(c)** | The device was **operating properly**. If it was not, that did not affect the record or its accuracy. | Same as 63(2)(a). |
| **63(2)(d)** | The record **reproduces or is derived from** information fed in the ordinary course. | Same as 63(2)(a). |
| **63(3)** | Several devices used for the purpose are treated as **one device**, whether used (a) standalone, (b) on a computer system, (c) on a computer network, (d) on a computer resource, or (e) through an intermediary. | Allow **several devices or sources per evidence record**, for example a phone, a Google Drive backup and the WhatsApp service. |
| **63(4)(a)** | The certificate must identify the record and **describe the manner in which it was produced**. | Required field `manner_of_production`, e.g. "WhatsApp › Export chat › Include media on Samsung SM-S918B, 12/10/2026". |
| **63(4)(b)** | Particulars of **any device involved**, to show it is a device under 63(3)(a)–(e). | Device fields (see 2.2). |
| **63(4)(c)** | Deal with the 63(2) conditions. Signed by the **person in charge** of the device or the relevant activities **and an expert**. Stated "to the best of the knowledge and belief". Uses the certificate "**specified in the Schedule**". | A two-part certificate with two signatories, in the Schedule format. |
| **63(4)** (opening words) | The certificate is submitted with the record "**at each instance where it is being submitted for admission**". | A new certificate **version** for each submission or proceeding. |
| **63(5)** | Information is supplied, and output produced, "with or without human intervention" or via "appropriate equipment". | No feature needed. Shown as an explanatory note in the wizard. |

Verbatim text of **Section 63(4)** (embed it in the app's help panel):

> (4) In any proceeding where it is desired to give a statement in evidence by virtue of this section, a certificate doing any of the following things shall be submitted along with the electronic record at each instance where it is being submitted for admission, namely:—
> (a) identifying the electronic record containing the statement and describing the manner in which it was produced;
> (b) giving such particulars of any device involved in the production of that electronic record as may be appropriate for the purpose of showing that the electronic record was produced by a computer or a communication device referred to in clauses (a) to (e) of sub-section (3);
> (c) dealing with any of the matters to which the conditions mentioned in sub-section (2) relate,
> and purporting to be signed by a person in charge of the computer or communication device or the management of the relevant activities (whichever is appropriate) and an expert shall be evidence of any matter stated in the certificate; and for the purposes of this sub-section it shall be sufficient for a matter to be stated to the best of the knowledge and belief of the person stating it in the certificate specified in the Schedule.

### 2.2 Schedule field map: every field in Part A and Part B

| Schedule field | Part A (Party) | Part B (Expert) | App field / type | Filled by |
|---|---|---|---|---|
| Heading "THE SCHEDULE [See section 63(4)(c)] CERTIFICATE" | ✓ | ✓ | fixed text | statute |
| "(To be filled by the Party)" / "(To be filled by the Expert)" | ✓ | ✓ | fixed text | statute |
| I, ___ (Name) | ✓ | ✓ | `full_name` text | user |
| Son/daughter/spouse of ___ | ✓ | ✓ | `relation_name` text | user |
| residing/employed at ___ | ✓ | ✓ | `address_or_employer` text | user |
| "do hereby solemnly affirm and sincerely state and submit as follows" | ✓ | ✓ | fixed text | statute |
| Device / digital record source (tick): **Computer / Storage Media, DVR, Mobile, Flash Drive, CD/DVD, Server, Cloud, Other** | ✓ | ✓ | multi-select enum, plus `category_other` text | user (app suggests one from the file type) |
| Make & Model | ✓ | ✓ | text | user (pre-filled from EXIF Make/Model when present) |
| Color | ✓ | ✓ | text | user |
| Serial Number | ✓ | ✓ | text | user |
| IMEI/UIN/UID/MAC/Cloud ID (as applicable) | ✓ | ✓ | list of `{type, value}`. IMEI: 15 digits with Luhn check. MAC: `AA:BB:CC:DD:EE:FF` | user |
| Any other relevant information about the device/digital record (specify) | ✓ | ✓ | textarea | user, plus an auto-generated metadata summary |
| Lawful control / working properly / regularly fed paragraph | ✓ | ✗ | fixed statutory text. **The user must tick an acknowledgement before generating** | statute + user |
| Owned / Maintained / Managed / Operated "by me (select as applicable)" | ✓ | ✗ *(verify against the official PDF)* | multi-select enum | user |
| HASH value/s of the electronic/digital record/s | ✓ | ✓ | from `evidence_files` | **auto** |
| Algorithm: SHA1 / SHA256 / MD5 / Other (Legally acceptable standard) | ✓ | ✓ | enum, default SHA256 | **auto** |
| "(Hash report to be enclosed with the certificate)" | ✓ | ✓ | generated annexure PDF | **auto** |
| (Name and signature) | ✓ | — | blank signature box | signed by hand or digital signature outside the app |
| (Name, designation and signature) | — | ✓ | `designation` text + blank signature box | expert |
| Date (DD/MM/YYYY) | ✓ | ✓ | date, always printed as `DD/MM/YYYY` | user (defaults to today, IST) |
| Time (IST): ___ hours (In 24 hours format) | ✓ | ✓ | `HH:MM`, Asia/Kolkata | user (defaults to now, IST) |
| Place | ✓ | ✓ | text | user |

### 2.3 Statutory text to embed (`lib/legal/schedule-63.ts`, word for word)

Store this as constants with `SCHEDULE_VERSION = "BSA-2023-original"`. **Do not paraphrase it.** Render `☐` / `☑` for the tick boxes.

```text
THE SCHEDULE
[See section 63(4)(c)]
CERTIFICATE

PART A
(To be filled by the Party)

I, ________ (Name), Son/daughter/spouse of ________ residing/employed at ________ do hereby solemnly affirm and sincerely state and submit as follows:—

I have produced electronic record/output of the digital record taken from the following device/digital record source (tick mark):—

Computer / Storage Media ☐   DVR ☐   Mobile ☐   Flash Drive ☐
CD/DVD ☐   Server ☐   Cloud ☐   Other ☐
Other: ________

Make & Model: ________   Color: ________
Serial Number: ________
IMEI/UIN/UID/MAC/Cloud ID ________ (as applicable)
and any other relevant information, if any, about the device/digital record ________ (specify).

The digital device or the digital record source was under the lawful control for regularly creating, storing or processing information for the purposes of carrying out regular activities and during this period, the computer or the communication device was working properly and the relevant information was regularly fed into the computer during the ordinary course of business. If the computer/digital device at any point of time was not working properly or out of operation, then it has not affected the electronic/digital record or its accuracy. The digital device or the source of the digital record is:—

Owned ☐   Maintained ☐   Managed ☐   Operated ☐
by me (select as applicable).

I state that the HASH value/s of the electronic/digital record/s is ________, obtained through the following algorithm:—
SHA1: ☐
SHA256: ☐
MD5: ☐
Other ________ (Legally acceptable standard)

(Hash report to be enclosed with the certificate)

(Name and signature)
Date (DD/MM/YYYY):
Time (IST): ________ hours (In 24 hours format)
Place:

PART B
(To be filled by the Expert)

I, ________ (Name), Son/daughter/spouse of ________ residing/employed at ________ do hereby solemnly affirm and sincerely state and submit as follows:—

The produced electronic record/output of the digital record are obtained from the following device/digital record source (tick mark):—

Computer / Storage Media ☐   DVR ☐   Mobile ☐   Flash Drive ☐
CD/DVD ☐   Server ☐   Cloud ☐   Other ☐
Other: ________

Make & Model: ________   Color: ________
Serial Number: ________
IMEI/UIN/UID/MAC/Cloud ID ________ (as applicable)
and any other relevant information, if any, about the device/digital record ________ (specify).

I state that the HASH value/s of the electronic/digital record/s is ________, obtained through the following algorithm:—
SHA1: ☐
SHA256: ☐
MD5: ☐
Other ________ (Legally acceptable standard)

(Hash report to be enclosed with the certificate)

(Name, designation and signature)
Date (DD/MM/YYYY):
Time (IST): ________ hours (In 24 hours format)
Place:
```

### 2.4 Practical points from commentary (secondary sources; the bare Act controls)

| Point | Source | What the app does |
|---|---|---|
| Part A is filled by the party or the person in charge of the device. Part B is filled by an expert. | section69bns.com and other guides | Two separate wizard steps, each with its own signatory details. |
| Whether the Part B expert must be a notified "Examiner of Electronic Evidence" (s.79A IT Act) is debated. | legalspaceservices.in, innefu.com | Make expert qualification a free-text field and show a "confirm with counsel" note. Do not hard-code a rule. |
| Courts and commentators disagree on whether the hash should be of the **original** record or of the **copy** produced. | indianlawlive.net | Store **two** hashes: (1) the hash the expert or party computed at acquisition, typed in, and (2) the hash the platform computed on receipt. Show match or mismatch. |
| No certificate is needed when the original device itself is produced as primary evidence. (*Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal*, (2020) 7 SCC 1, decided under s.65B IEA.) | case law | Show an information note only. The app does not decide whether a certificate is needed. |
| *Pune Bar Association v. Union of India* challenges s.63(4) and the Schedule. | indiankanoon.org | Check the current status before a commercial launch. Keep the template versioned so it can be updated. |
| The section69bns.com article explains the fields, but per web-search summaries it does not reproduce the full statutory Schedule. | section69bns.com | Use it for explanations only. Section 2.3 above is the template. |

---

## 3. Claude Code build specification (Phase 1 MVP: no login, runs in the browser)

### 3.1 Goal
Build a **static, browser-only** MVP. There is **no login and no backend**. Hashing, metadata extraction and PDF generation all run in the user's browser, and **evidence files are never uploaded anywhere**. Data is kept in the browser's IndexedDB, and the user can export and import a "case bundle" as a backup. The build output is plain static files that can be hosted on **GitHub Pages** or **AWS** (see Section 4).

The user flow:
1. Create an **Evidence** record.
2. Add files. The app hashes them and extracts metadata.
3. Fill in device and declarant details.
4. Generate a **draft Section 63 certificate PDF** (Part A + Part B + Hash Report annexure).

Every action is written to a local, hash-chained audit log.

Why browser-only for the MVP:
- No login is needed.
- Sensitive evidence never leaves the user's device.
- There's no server cost.
- GitHub Pages can host it.
- Phase 2 can add login and cloud storage (Appendix A) without rewriting the front end.

### 3.2 Non-negotiable rules
1. Reproduce the Schedule text from Section 2.3 **exactly**. Store it in one file (`lib/legal/schedule-63.ts`) and never generate it with an LLM or paraphrase it.
2. The app never states or implies that it has certified anything. Every PDF page carries the footer: *"Draft prepared with [AppName] on DD/MM/YYYY HH:MM IST. Not valid until verified and signed by the declarant (Part A) and the expert (Part B)."*
3. Signature areas are left **blank**. No auto-signatures or typed-name signatures.
4. The 63(2) declaration in Part A cannot be edited. The user must tick: *"I have read and understood this declaration and it is true to the best of my knowledge and belief."*
5. Dates are printed as `DD/MM/YYYY`. Times are printed as `HH:MM` in 24-hour IST (`Asia/Kolkata`).
6. Every certificate is a new immutable **version**. Finalising locks the version and stores the PDF's own SHA-256.
7. **No file content leaves the browser.** No analytics or error-reporting SDK may receive file data. Add a Content-Security-Policy `<meta>` tag with `connect-src 'self'` so the browser itself blocks uploads. Show this notice on the home page: *"Your files are processed only in this browser and are never uploaded."*

### 3.3 Tech stack
- **Framework:** Next.js 15 (App Router) with **`output: 'export'`** (static site), TypeScript `strict`. Static export has these limits, and the app must follow all of them:
  - no API routes, server actions or middleware;
  - **no dynamic route segments**: use query strings such as `/evidence/?id=…` and read them with `useSearchParams` inside `<Suspense>`;
  - `images: { unoptimized: true }`;
  - `trailingSlash: true`;
  - `basePath` read from `NEXT_PUBLIC_BASE_PATH`.
- **UI:** Tailwind CSS, shadcn/ui, lucide-react, react-hook-form + zod
- **Local database:** IndexedDB via `dexie` + `dexie-react-hooks`
- **Hashing:** `hash-wasm` (`createSHA256`, `createSHA1`, `createMD5`). Read the file in 4 MB chunks (`file.slice().arrayBuffer()`) and compute all three hashes in **one pass** inside a **Web Worker** with a progress bar. Don't use `crypto.subtle`, because it can't do MD5 and loads the whole file into memory.
- **File detection:** `file-type` (`fileTypeFromBlob`, which reads magic bytes rather than the file extension)
- **Metadata:** `exifr` (images), `music-metadata` (`parseBlob` for audio and video containers), `pdf-lib` (PDF info), `jszip` (WhatsApp `.zip` exports and case bundles)
- **PDF:** `@react-pdf/renderer` in the browser (`pdf(<CertificateDocument/>).toBlob()`), lazy-loaded
- **Dates:** `date-fns` + `date-fns-tz` (`Asia/Kolkata`)
- **Tests:** Vitest for `lib/`. Playwright runs one end-to-end happy path against the static build (`next build && npx serve out`).

### 3.4 Local data model (Dexie / IndexedDB)
Field names match the Phase 2 SQL in Appendix A, so data can later be synced to the cloud unchanged.

```ts
// lib/db.ts
db.version(1).stores({
  evidence:     'id, status, createdAt, updatedAt',
  files:        'id, evidenceId, sha256',
  blobs:        'fileId',                       // the File/Blob itself (optional copy)
  devices:      'id, evidenceId',
  certificates: 'id, evidenceId, [evidenceId+version], status',
  auditEvents:  '++seq, evidenceId, certificateId, action, createdAt',
  settings:     'key',                          // default declarant/expert profile, app prefs
});

type EvidenceType   = 'image'|'audio'|'video'|'document'|'whatsapp_export'|'email'|'other';
type DeviceCategory = 'computer_storage_media'|'dvr'|'mobile'|'flash_drive'|'cd_dvd'|'server'|'cloud'|'other';
type ControlType    = 'owned'|'maintained'|'managed'|'operated';
type IdentifierType = 'imei'|'uin'|'uid'|'mac'|'cloud_id'|'other';
type HashAlgo       = 'sha256'|'sha1'|'md5'|'other';

interface Evidence { id: string; title: string; description?: string; evidenceType: EvidenceType;
  mannerOfProduction?: string /* s.63(4)(a) */; acquiredAt?: string;
  status: 'draft'|'hashed'|'certificate_drafted'|'finalised'|'archived'; createdAt: string; updatedAt: string; }

interface EvidenceFile { id: string; evidenceId: string; originalFilename: string; declaredMime?: string; detectedMime?: string;
  sizeBytes: number; lastModified?: string; sha256: string; sha1: string; md5: string; hashedAt: string;
  acquisitionHash?: string; acquisitionHashAlgo?: HashAlgo; acquisitionHashMatch?: boolean;
  metadata: Record<string, unknown>; blobStored: boolean; }

interface Device { id: string; evidenceId: string; categories: DeviceCategory[]; categoryOther?: string;
  makeModel?: string; color?: string; serialNumber?: string; otherInfo?: string; control: ControlType[];
  identifiers: { idType: IdentifierType; value: string }[]; }

interface Certificate { id: string; evidenceId: string; version: number; scheduleVersion: 'BSA-2023-original';
  courtName?: string; caseNumber?: string; partA: PartA; partB: PartB; hashAlgo: HashAlgo;
  declarationAcknowledgedAt?: string; status: 'draft'|'finalised'; pdfSha256?: string; createdAt: string; }

interface AuditEvent { seq?: number; action: string; evidenceId?: string; certificateId?: string;
  details: Record<string, unknown>; userAgent: string; createdAt: string; prevHash: string; rowHash: string; }
```

**Audit log rules**
- Only `lib/audit/append.ts` may write to `auditEvents`. Don't export any update or delete function.
- Each row stores `rowHash = sha256(prevHash + canonicalJSON(row))`. The Audit screen has a "Verify chain" button.
- Actions to log:
  - `evidence.create`, `evidence.update`
  - `file.add`, `file.hash`, `file.reverify`
  - `certificate.generate`, `certificate.finalise`, `certificate.download`
  - `bundle.export`, `bundle.import`
- Show this limitation in the UI and the README: a browser-local log detects edits, but the user can delete it by clearing site data. A server-side log comes in Phase 2.

### 3.5 File handling and hashing flow
1. The user drops files, or picks them with the file picker. Nothing is uploaded.
2. A Web Worker computes **SHA-256, SHA-1 and MD5 in one pass** and shows progress. The results are saved to `files` and logged as `file.hash`.
3. Detect the real MIME type with `file-type` and extract metadata (3.6).
4. The option *"Keep a copy of the file in this browser"* is on by default:
   - The file is stored in `blobs`.
   - Call `navigator.storage.persist()`.
   - Show the space used and left with `navigator.storage.estimate()`.
   - Warn when the file is close to the browser's storage quota.
   - If the user turns the option off, only the hashes and metadata are kept, and the user must keep the original file.
5. **Re-verify:** the user re-selects the original, or the app uses the stored copy. The app re-hashes it, compares the result with the stored SHA-256 and logs `file.reverify` with match or mismatch.
6. Acquisition hash: the user can type in a hash the expert or party computed when the evidence was collected. The app compares it with the computed hash (see 2.4).
7. Hashing streams in chunks, so files of several GB work.

### 3.6 Metadata extraction by type
| Type | Extract | Suggested device category |
|---|---|---|
| Image | EXIF Make, Model, DateTimeOriginal, GPS (if present), software, dimensions. Note that screenshots often have no EXIF. | Mobile / Computer |
| Audio | duration, codec, bitrate, sample rate, container tags, creation date | Mobile |
| Video | duration, container, codec, resolution, creation date (via `music-metadata`) | Mobile / DVR (CCTV) |
| PDF / document | page count, author, producer, creation and modification dates | Computer / Storage Media |
| WhatsApp export (`.txt` or `.zip`) | Parse Android `DD/MM/YY, HH:MM - Name: msg` and iOS `[DD/MM/YY, HH:MM:SS] Name: msg`. Extract participants, first and last message date, message count and media files. **Hash the zip and every file inside it.** | Mobile + Cloud |
| Other | size, detected MIME, last-modified time | Other |

### 3.7 Certificate generation
- Wizard steps:
  1. Evidence and files: review hashes, `mannerOfProduction`, court and case number.
  2. Device(s).
  3. **Part A**: party details (pre-filled from Settings → My details), control type, declaration acknowledgement.
  4. **Part B**: expert name, relation, address/employer, designation, qualification note.
  5. Date, time and place.
  6. Preview.
  7. Generate.
- Output, A4, one PDF, generated in the browser and downloaded:
  - Part A on page 1 onward.
  - Part B on a new page.
  - **Annexure: Hash Report.** One row per file with: filename, size in bytes, detected MIME, SHA-256, SHA-1, MD5, acquisition hash and match status, time computed (IST), tool (`hash-wasm <version> in <browser>`), evidence ID and file ID.
- Print hash values in a monospace font with wrapping, and never truncate them.
- **Tick boxes:** draw each one as a small bordered square, with a tick for selected options. Don't use the ☐/☑ characters, because react-pdf's built-in fonts can't display them. If you use them anyway, bundle a font that includes them, such as Noto Sans Symbols 2, in `public/fonts`.
- Show a `DRAFT` watermark until the user finalises the version. On finalise, compute and store `pdfSha256` and log it.

### 3.8 Screens and routes (static export: query strings, not `[id]` folders)
| Route | Screen | Key components |
|---|---|---|
| `/` | Dashboard | evidence list, certificate drafts, recent activity, counts, privacy notice |
| `/evidence/new/` | New Evidence | title, type, `mannerOfProduction`, drag-and-drop, per-file hash progress, detected type, metadata panel |
| `/evidence/?id=…` | Evidence Detail | files with hashes, re-verify, devices, certificate versions, audit timeline |
| `/certificate/?evidenceId=…` | Certificate Wizard | the steps in 3.7, a statute help panel (s.63 text), PDF preview |
| `/audit/` | Audit Log | filterable events, "Verify chain", export as JSON |
| `/settings/` | My Details & Backup | default declarant and expert profile, **Export case bundle**, **Import case bundle**, storage usage, clear data |

### 3.9 Case bundle (backup / move to another computer)
- `.zip` containing:
  - `manifest.json`: all records for the selected evidence;
  - `files/<fileId>/<originalFilename>` (when the copy is stored);
  - `certificates/<id>-v<version>.pdf`;
  - `audit.json`;
  - `SHA256SUMS.txt`: one line per file in the bundle.
- On import, verify every file against `SHA256SUMS.txt` and the stored hashes before saving anything. Log `bundle.import` with the result.

### 3.10 Folder structure
```
app/page.tsx                      (dashboard)
app/evidence/new/page.tsx
app/evidence/page.tsx             (detail, reads ?id=)
app/certificate/page.tsx          (wizard, reads ?evidenceId=)
app/audit/page.tsx
app/settings/page.tsx
lib/db.ts
lib/evidence/   hash.worker.ts, hashing.ts, detect.ts, metadata/{image,audio,video,pdf,whatsapp}.ts
lib/legal/      schedule-63.ts, section-63.ts, validators.ts (IMEI Luhn, MAC)
lib/pdf/        CertificateDocument.tsx, HashReport.tsx, Checkbox.tsx
lib/audit/      append.ts, verify.ts
lib/bundle/     export.ts, import.ts
lib/billing/    (empty placeholder, Phase 2)
.github/workflows/deploy-pages.yml
```

### 3.11 Phase 1 acceptance criteria
- [ ] `npm run build` produces a static `out/` folder. The app works when served from a sub-path (`NEXT_PUBLIC_BASE_PATH=/repo-name`).
- [ ] The browser DevTools Network tab shows **no request carrying file content** while hashing, generating or exporting.
- [ ] Image, audio, video, PDF and WhatsApp `.zip` files all work. The real MIME type is detected.
- [ ] SHA-256, SHA-1 and MD5 match `sha256sum`, `sha1sum` and `md5sum` for the test fixtures (Vitest).
- [ ] Device and identifier fields work. IMEI is validated with the Luhn check.
- [ ] The PDF contains Part A, Part B and the Hash Report, with Schedule wording matching Section 2.3 exactly (unit test compares it with the constants). Tick boxes render correctly.
- [ ] Dates appear as `DD/MM/YYYY` and times as `HH:MM` IST in 24-hour format.
- [ ] Every action in 3.4 creates an audit event, and "Verify chain" passes. Editing a row in DevTools makes it fail.
- [ ] Finalised certificate versions are read-only, and their `pdfSha256` is stored.
- [ ] Exporting a case bundle, clearing site data and importing it again restores everything, and all hashes verify.
- [ ] Deploys to GitHub Pages through the workflow in 4.1.

### 3.12 Later phases (design for these, don't build them)
- **Phase 2, login and cloud:**
  - Supabase Auth (email + password).
  - Cloud storage of evidence, using the Appendix A schema with RLS.
  - Server-side hash re-verification with a Supabase Edge Function.
  - Server-side audit log.
  - Sync of local IndexedDB data to the cloud account.
- **Phase 2:**
  - An expert account role that receives Part B requests.
  - Razorpay payment per certificate (`lib/billing`).
- **Phase 3:**
  - Aadhaar eSign or DSC signing.
  - `ffprobe` video analysis and `.eml` email parsing.
  - Hindi certificate rendering.
  - DPDP Act 2023 consent and notice, and a data-retention policy. These are needed as soon as evidence is stored on a server.

### 3.13 Environment variables (Phase 1)
```
NEXT_PUBLIC_BASE_PATH=            # "" for a custom domain or AWS root; "/<repo-name>" for GitHub Pages project sites
NEXT_PUBLIC_APP_NAME="Section 63 Draft Certificate Tool"
```

---

## 4. Hosting

**Recommendation:** use **GitHub Pages** for the MVP. It's free, deploys on every push and takes the least setup. Move to **AWS Amplify** when Phase 2 needs a server or you want a custom domain hosted in India. **S3 + CloudFront** is the cheapest AWS option, but it takes the most steps.

All three serve the same `out/` folder. In Phase 1 no evidence is stored on the host, so the hosting region doesn't matter for evidence yet.

### 4.0 Shared setup (needed for every option)
1. Create a **new** GitHub repository, e.g. `bsa63-certificate`. Don't build it inside the `awesome` fork.
2. `next.config.ts`:
   ```ts
   import type { NextConfig } from 'next';
   const nextConfig: NextConfig = {
     output: 'export',
     basePath: process.env.NEXT_PUBLIC_BASE_PATH || '',
     trailingSlash: true,
     images: { unoptimized: true },
   };
   export default nextConfig;
   ```
3. `package.json` scripts: `"build": "next build"`, `"test": "vitest run"`.
4. Check locally: run `npm run build`, then `npx serve out` and open the printed URL.

### 4.1 GitHub Pages (recommended for the MVP)
1. Push the project to `main` in the new repo. On a **free** GitHub plan, the repo must be **public** to use Pages; private repos need GitHub Pro or a Team plan. A public repo is fine here because only the source code is public, and evidence never leaves the user's browser.
2. In the repo, go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
3. Add `.github/workflows/deploy-pages.yml`:
   ```yaml
   name: Deploy to GitHub Pages
   on:
     push:
       branches: [main]
     workflow_dispatch:
   permissions:
     contents: read
     pages: write
     id-token: write
   concurrency:
     group: pages
     cancel-in-progress: false
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v5
         - uses: actions/setup-node@v5
           with:
             node-version: 22
             cache: npm
         - run: npm ci
         - run: npm run test --if-present
         - run: npm run build
           env:
             NEXT_PUBLIC_BASE_PATH: /${{ github.event.repository.name }}
         - uses: actions/upload-pages-artifact@v4
           with:
             path: out
     deploy:
       needs: build
       runs-on: ubuntu-latest
       environment:
         name: github-pages
         url: ${{ steps.deployment.outputs.page_url }}
       steps:
         - id: deployment
           uses: actions/deploy-pages@v4
   ```
4. Commit and push. Watch the run in the **Actions** tab. The site goes live at `https://<your-username>.github.io/bsa63-certificate/`.
5. **Custom domain (optional):**
   1. Go to **Settings → Pages → Custom domain** and enter e.g. `certify.example.in`.
   2. At your DNS provider, add a `CNAME` record: `certify` → `<your-username>.github.io`.
   3. Tick **Enforce HTTPS**.
   4. In the workflow, change `NEXT_PUBLIC_BASE_PATH` to an empty string, because the site now lives at the domain root.
6. GitHub Pages can't set custom HTTP headers, so the Content-Security-Policy goes in a `<meta>` tag in `app/layout.tsx` (rule 7 in 3.2). Start from this and loosen only what a library actually needs:
   `default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-src blob:; object-src 'none'; base-uri 'self'; form-action 'none'`

### 4.2 AWS Amplify Hosting (easiest AWS option, and it also supports Phase 2 server features)
1. In the AWS Console, open **AWS Amplify → Create new app → GitHub**. Authorize access and pick the `bsa63-certificate` repo and the `main` branch. Region: **Asia Pacific (Mumbai) ap-south-1**.
2. Replace the build settings with this `amplify.yml`. It deploys the static `out/` folder:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: out
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
   ```
   Leave `NEXT_PUBLIC_BASE_PATH` unset, because Amplify serves the site at the root.
3. Click **Save and deploy**. You get a URL like `https://main.<app-id>.amplifyapp.com`, and every push to `main` redeploys.
4. **Custom domain:** go to **Hosting → Custom domains → Add domain**. Use your Route 53 domain, or follow the DNS records Amplify shows for an external registrar. Amplify issues the HTTPS certificate automatically.
5. **Headers:** Amplify can set real HTTP headers (**Hosting → Custom headers**). Move the CSP there as a `Content-Security-Policy` header.

### 4.3 AWS S3 + CloudFront (cheapest, most control)
1. **S3:** create a bucket, e.g. `bsa63-certificate-site`, in `ap-south-1`. Keep **Block all public access ON**.
2. **CloudFront:** go to **Create distribution**.
   - **Origin:** the S3 bucket.
   - **Origin access:** **Origin access control** (create a new one). When CloudFront offers the bucket policy, copy it into **S3 → bucket → Permissions → Bucket policy**.
   - **Viewer protocol policy:** Redirect HTTP to HTTPS.
   - **Default root object:** `index.html`.
3. **CloudFront Function** (viewer request). Without it, S3 won't serve `index.html` for paths like `/audit/`. Create the function and attach it to the default behaviour:
   ```js
   function handler(event) {
     var request = event.request;
     if (request.uri.endsWith('/')) {
       request.uri += 'index.html';
     } else if (!request.uri.includes('.')) {
       request.uri += '/index.html';
     }
     return request;
   }
   ```
4. **Error pages:** map 403 and 404 to `/404.html` with response code 404.
5. **Deploy manually** (needs the AWS CLI, configured):
   ```bash
   npm run build
   aws s3 sync out/ s3://bsa63-certificate-site --delete
   aws cloudfront create-invalidation --distribution-id <DISTRIBUTION_ID> --paths "/*"
   ```
6. **Custom domain:**
   1. Request a certificate in **ACM in `us-east-1`**. CloudFront only accepts certificates from that region. Validate it by DNS.
   2. Add the domain under **Alternate domain names** in the distribution.
   3. In Route 53, create an **A/AAAA alias** record pointing to the distribution.
7. **Security headers:** **CloudFront → Policies → Response headers** lets you attach the CSP and HSTS as real headers.
8. **Deploy automatically from GitHub** (no stored AWS keys; uses OIDC):
   1. In IAM, add the identity provider `token.actions.githubusercontent.com` (audience `sts.amazonaws.com`).
   2. Create a role whose trust policy only allows `repo:<your-username>/bsa63-certificate:ref:refs/heads/main`. Give it these permissions:
      - `s3:ListBucket` on the bucket;
      - `s3:PutObject` and `s3:DeleteObject` on `bucket/*`;
      - `cloudfront:CreateInvalidation` on the distribution.
   3. Add `.github/workflows/deploy-aws.yml`:
   ```yaml
   name: Deploy to AWS
   on:
     push:
       branches: [main]
   permissions:
     id-token: write
     contents: read
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v5
         - uses: actions/setup-node@v5
           with:
             node-version: 22
             cache: npm
         - run: npm ci
         - run: npm run build
         - uses: aws-actions/configure-aws-credentials@v4
           with:
             role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>
             aws-region: ap-south-1
         - run: aws s3 sync out/ s3://bsa63-certificate-site --delete
         - run: aws cloudfront create-invalidation --distribution-id ${{ vars.CLOUDFRONT_DISTRIBUTION_ID }} --paths "/*"
   ```
   Store the distribution ID as a repository **variable** (**Settings → Secrets and variables → Actions → Variables**).

### 4.4 Which one when
| Situation | Use |
|---|---|
| MVP, free, quickest | GitHub Pages (4.1) |
| Want AWS, custom domain, real security headers, little setup | Amplify (4.2) |
| Phase 2 with login: static front end + Supabase | Any of the three. Supabase is called straight from the browser, so the front end can stay static. |
| Phase 2 needs Next.js server features (API routes, SSR) | Amplify (4.2), with the `output: 'export'` line removed from the config. GitHub Pages and plain S3 can't run server code. |
| Lowest running cost with full control | S3 + CloudFront (4.3) |

---

## Appendix A: Phase 2 cloud schema (Supabase SQL; not used in Phase 1)

```sql
-- enums
create type evidence_type   as enum ('image','audio','video','document','whatsapp_export','email','other');
create type evidence_status as enum ('draft','hashed','certificate_drafted','finalised','archived');
create type device_category as enum ('computer_storage_media','dvr','mobile','flash_drive','cd_dvd','server','cloud','other');
create type control_type    as enum ('owned','maintained','managed','operated');
create type identifier_type as enum ('imei','uin','uid','mac','cloud_id','other');
create type hash_algo       as enum ('sha256','sha1','md5','other');

create table profiles (
  id uuid primary key references auth.users on delete cascade,
  full_name text, relation_name text, address_or_employer text, phone text,
  role text not null default 'party' check (role in ('party','expert','admin')),
  created_at timestamptz not null default now()
);

create table evidence (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users,
  title text not null, description text,
  evidence_type evidence_type not null default 'other',
  manner_of_production text,             -- s.63(4)(a)
  acquired_at timestamptz,
  status evidence_status not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table evidence_files (
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references evidence on delete cascade,
  storage_path text not null,
  original_filename text not null,
  declared_mime text, detected_mime text,
  size_bytes bigint not null,
  client_sha256 text,                    -- computed in browser
  sha256 text, sha1 text, md5 text,      -- computed on server (authoritative)
  hash_match boolean,                    -- client_sha256 = sha256
  acquisition_hash text, acquisition_hash_algo hash_algo, -- typed in by party/expert
  hashed_at timestamptz,
  metadata jsonb not null default '{}',
  uploaded_by uuid not null references auth.users,
  uploaded_at timestamptz not null default now()
);

create table devices (                   -- s.63(3): many devices per evidence
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references evidence on delete cascade,
  categories device_category[] not null,
  category_other text,
  make_model text, color text, serial_number text,
  other_info text,
  control control_type[] default '{}'    -- Part A: owned/maintained/managed/operated
);

create table device_identifiers (
  id uuid primary key default gen_random_uuid(),
  device_id uuid not null references devices on delete cascade,
  id_type identifier_type not null, value text not null
);

create table certificates (
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references evidence on delete cascade,
  version int not null,
  schedule_version text not null default 'BSA-2023-original',
  court_name text, case_number text,     -- "each instance" of submission
  part_a jsonb not null,                 -- declarant + selections snapshot
  part_b jsonb not null,                 -- expert details snapshot
  hash_algo hash_algo not null default 'sha256',
  declaration_acknowledged_at timestamptz,
  status text not null default 'draft' check (status in ('draft','finalised')),
  pdf_path text, pdf_sha256 text,
  hash_report_path text,
  created_by uuid not null references auth.users,
  created_at timestamptz not null default now(),
  unique (evidence_id, version)
);

create table audit_events (              -- append-only, hash-chained
  id bigserial primary key,
  actor_id uuid references auth.users,
  evidence_id uuid, certificate_id uuid,
  action text not null,                  -- e.g. 'evidence.create','file.upload','file.hash','certificate.generate','file.download','auth.login'
  details jsonb not null default '{}',
  ip inet, user_agent text,
  created_at timestamptz not null default now(),
  prev_hash text, row_hash text          -- sha256(prev_hash || canonical row)
);
```

- **RLS:** turn it on for every table. Users can select, insert and update only rows where they own the parent `evidence`.
- **audit_events:** insert and select only. Add a trigger that raises an error on UPDATE or DELETE. Add a `BEFORE INSERT` trigger that fills in `prev_hash` and `row_hash` (using `pgcrypto`).
- Once a certificate's `status = 'finalised'`, a trigger blocks any further edits to that row.

---

## Sources

**Primary (controls):**
- [Bharatiya Sakshya Adhiniyam, 2023 — official bare Act PDF (India Code)](https://www.indiacode.nic.in/bitstream/123456789/20063/1/a2023-47.pdf)
- [The Schedule [See section 63(4)(c)] — India Code schedule file](https://upload.indiacode.nic.in/schedulefile?aid=AC_CEN_5_23_00049_2023-47_1719292804654&rid=1163)
- [Section 63(4), BSA 2023 — Indian Kanoon](https://indiankanoon.org/doc/90089205/)

**Secondary (explanations only):**
- [Section 63 BSA Certificate Format — section69bns.com](https://section69bns.com/section-63-bsa-certificate-format/)
- [Complete Guide to Electronic Evidence, Section 63 BSA — section69bns.com](https://section69bns.com/section-63-bsa/)
- [BSA Section 63: certificate format, expert signature, hash values — legalspaceservices.in](https://legalspaceservices.in/bsa-63-electronic-evidence-certificate.php)
- [Section 63 BSA Certificate: Parts A and B, Hash Value — innefu.com](https://innefu.com/section-63-bsa-certificate-guide/)
- [Hash of original vs copy — indianlawlive.net](https://indianlawlive.net/2025/06/29/sakshya-adhiniyam-doesnt-mandate-hashing-copy-pen-drive-or-cd-produced-it-mandates-hashing-original-only/)
- [Hash Value Certificate: mandatory or directory? — indianlawlive.net](https://indianlawlive.net/2025/07/02/hash-value-certificate-mandatory-or-directory/)
- [Pune Bar Association v. Union of India — Indian Kanoon](https://indiankanoon.org/doc/5836207/)
- [Electronic evidence admissibility under s.63 — LiveLaw](https://www.livelaw.in/articles/electronic-evidence-admissibility-section-63-bhartiya-saksha-adhiniyam-2023-261511)
