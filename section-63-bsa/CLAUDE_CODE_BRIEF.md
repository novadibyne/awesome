# BSA Section 63 Certificate Platform — Brief for Claude Code

> **How to use this file:** put it in an empty project folder, open Claude Code there and say:
> *"Read CLAUDE_CODE_BRIEF.md and build Phase 1 exactly as specified. Use the statutory text in Section 2.3 word for word. Ask me before deviating from it."*

Proof-of-concept web app: users upload electronic evidence, the app extracts technical metadata, computes hashes, and drafts the certificate in the format prescribed by the **Schedule to Section 63(4)(c) of the Bharatiya Sakshya Adhiniyam, 2023 (BSA, Act 47 of 2023)**.

> ⚠️ **Verify before production:** the statutory wording in Section 2 is reproduced from the BSA bare Act. Check punctuation and layout against the official India Code PDF (link in Sources) before going live. If the official text and any website differ, **the official text wins.**

---

## 1. Your request vs my suggestion vs what you want

| # | Your original request | My suggestion | What you want (build requirement for Claude Code) |
|---|---|---|---|
| 1 | An interface to upload pictures, recordings, WhatsApp messages and other evidence. | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui, with a drag-and-drop uploader. | A responsive web app that accepts images, audio, video, PDFs/documents, WhatsApp chat exports (`.txt` or `.zip` with media) and any other file as generic evidence. |
| 2 | Generate certificates under Section 63 BSA. | Generate a PDF that reproduces the **Schedule word for word**: Part A (Party) and Part B (Expert), plus the hash report annexure the Schedule asks for. | A certificate wizard that pre-fills the technical fields (hashes, file details, device metadata) and outputs a **draft** PDF in the exact Schedule format. Signature boxes stay blank so the people concerned can sign. |
| 3 | *(implied by the certificate)* Hash values. | SHA-256 as the default. Also compute MD5 and SHA-1 because the Schedule lists all three. Hash on the server, not only in the browser. | Compute and store SHA-256 (plus MD5 and SHA-1) for every file. Generate the hash report annexure. Flag any mismatch between the browser hash and the server hash. |
| 4 | Track user logs. | Supabase PostgreSQL with an append-only `audit_events` table, hash-chained so tampering can be detected. | Log logins, uploads, hash computation, edits, certificate generation and downloads, with IST timestamp, IP, user agent and document version. |
| 5 | Possibly a login page. | Supabase Auth (email + password) with Row Level Security. | Registration, login and a dashboard. Each user sees only their own evidence. |
| 6 | Possibly payment per certificate. | Design for Razorpay later. Not part of the MVP. | Payments are an optional future module. Leave room in the data model, but write no payment code in Phase 1. |
| 7 | Build a proof of concept first. | One Next.js app plus Supabase. No microservices. | A working local MVP: upload → hash → metadata → certificate draft → history. |
| 8 | Possibly commercialise later. | Keep evidence processing, legal templates and billing in separate modules. | Modular code (`lib/evidence`, `lib/legal`, `lib/billing`) so it can grow into a SaaS. |
| 9 | — *(added in my suggestion)* | Build around an **Evidence** record, not a Certificate record. | `Evidence` is the central entity. Files, devices, hash reports, certificate versions and audit events all belong to it. |
| 10 | — *(added in my suggestion)* | The app **drafts**. It cannot certify. | Clear disclaimers. The Section 63(2) declarations are made by the party, and Part B is signed by an expert. The app only pre-fills technical facts and stamps the PDF "DRAFT". |
| 11 | — *(added in my suggestion)* | Section 63(4) requires a certificate "at each instance" the record is submitted. | Certificates are versioned for each submission, with court and case number recorded. |

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

## 3. Claude Code build specification (Phase 1 MVP)

### 3.1 Goal
Build a local, working MVP. A logged-in user creates an **Evidence** record, uploads one or more files, the app hashes them and extracts metadata, the user fills device and declarant details, and the app generates a **draft Section 63 certificate PDF (Part A + Part B + Hash Report annexure)**. Every action is audit-logged.

### 3.2 Non-negotiable legal rules
1. Reproduce the Schedule text from Section 2.3 **exactly**. Store it in one file (`lib/legal/schedule-63.ts`) and never generate it with an LLM or paraphrase it.
2. The app never states or implies that it has certified anything. Every PDF page carries the footer: *"Draft prepared with [AppName] on DD/MM/YYYY HH:MM IST. Not valid until verified and signed by the declarant (Part A) and the expert (Part B)."*
3. Signature areas are left **blank**. No auto-signatures or typed-name signatures.
4. The 63(2) declaration in Part A cannot be edited. The user must tick: *"I have read and understood this declaration and it is true to the best of my knowledge and belief."*
5. Dates are printed as `DD/MM/YYYY`. Times are printed as `HH:MM` in 24-hour IST (`Asia/Kolkata`).
6. Every certificate is a new immutable **version**. Finalising locks the version and stores the PDF's own SHA-256.

### 3.3 Tech stack
- **Framework:** Next.js 15 (App Router), TypeScript `strict`, React Server Components where sensible
- **UI:** Tailwind CSS, shadcn/ui, lucide-react, react-hook-form + zod
- **Backend:** Supabase (Auth, Postgres, Storage), `@supabase/ssr`
- **Hashing:** Node `crypto` (streaming `createHash`) on the server. `hash-wasm` in the browser for the on-upload preview.
- **File detection:** `file-type` (magic bytes, not the file extension)
- **Metadata:** `exifr` (images), `music-metadata` (audio/video container tags, duration), `pdf-lib` (PDF info), `jszip` (WhatsApp `.zip` exports)
- **PDF:** `@react-pdf/renderer`, server-side
- **Dates:** `date-fns` + `date-fns-tz` (`Asia/Kolkata`)
- **Tests:** Vitest for `lib/`, Playwright for one end-to-end happy path

### 3.4 Data model (Supabase SQL migrations)

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

### 3.5 Storage, upload and hashing flow
1. Store files in a private bucket `evidence` at `{user_id}/{evidence_id}/{file_id}/{original_filename}`.
2. The browser computes SHA-256 with `hash-wasm` while uploading and shows it straight away.
3. After upload, call `POST /api/files/[id]/hash`. The server streams the object from Storage and computes **SHA-256, SHA-1 and MD5 in one pass**. It stores them, sets `hash_match` and writes an audit event.
4. Detect the real file type with `file-type` and extract metadata (3.6). Store it in `metadata`.
5. Downloads use short-lived signed URLs (60 seconds), and every download is audit-logged.
6. Upload limit: 50 MB per file in Phase 1, configurable through `MAX_UPLOAD_MB`.

### 3.6 Metadata extraction by type
| Type | Extract | Suggested device category |
|---|---|---|
| Image | EXIF Make, Model, DateTimeOriginal, GPS (if present), software, dimensions. Note that screenshots often have no EXIF. | Mobile / Computer |
| Audio | duration, codec, bitrate, sample rate, container tags, creation date | Mobile |
| Video | duration, container, codec, resolution, creation date (via `music-metadata`). Full `ffprobe` waits for Phase 2. | Mobile / DVR (CCTV) |
| PDF / document | page count, author, producer, creation and modification dates | Computer / Storage Media |
| WhatsApp export (`.txt` or `.zip`) | Parse Android `DD/MM/YY, HH:MM - Name: msg` and iOS `[DD/MM/YY, HH:MM:SS] Name: msg`. Extract participants, first and last message date, message count and media files. **Hash the zip and every file inside it.** | Mobile + Cloud |
| Other | size, detected MIME | Other |

### 3.7 Certificate generation
- Wizard steps:
  1. Evidence and files: review hashes, `manner_of_production`, court and case number.
  2. Device(s).
  3. **Part A**: party details, control type, declaration acknowledgement.
  4. **Part B**: expert name, relation, address/employer, designation, qualification note.
  5. Date, time and place.
  6. Preview.
  7. Generate.
- Output, A4, one PDF:
  - Part A on page 1 onward.
  - Part B on a new page.
  - **Annexure: Hash Report.** One row per file with: filename, size in bytes, detected MIME, SHA-256, SHA-1, MD5, acquisition hash (if entered) with match status, time computed (IST), tool (`Node.js crypto <version>`), evidence ID and file ID.
- Print hash values in a monospace font with wrapping, and never truncate them.
- Tick boxes appear as `☑` or `☐` based on the selections.
- Show a `DRAFT` watermark until the user finalises the version. When finalised, compute and store `pdf_sha256` and log it.

### 3.8 Screens
| Screen | Purpose | Key components |
|---|---|---|
| Login / Register | Supabase Auth | email + password, reset password |
| Dashboard | Overview | evidence list, certificate drafts, recent activity, counts |
| New Evidence / Upload | Create a record and add files | drag-and-drop, per-file progress, live SHA-256, detected type, metadata panel |
| Evidence Detail | One evidence item | files with hashes, devices, certificate versions, audit timeline |
| Certificate Wizard | Draft the Schedule certificate | the steps in 3.7, a statute help panel (s.63 text), PDF preview |
| Evidence History / Audit | Activity trail | filterable `audit_events` table with hash-chain verification status |

### 3.9 Suggested folder structure
```
app/(auth)/login, register
app/(app)/dashboard, evidence/[id], evidence/new, evidence/[id]/certificate/new, audit
app/api/files/[id]/hash/route.ts
app/api/certificates/[id]/pdf/route.ts
lib/evidence/   hashing.ts, detect.ts, metadata/{image,audio,video,pdf,whatsapp}.ts
lib/legal/      schedule-63.ts, section-63.ts, validators.ts (IMEI Luhn, MAC)
lib/pdf/        CertificateDocument.tsx, HashReport.tsx
lib/audit/      log.ts
lib/billing/    (empty placeholder, Phase 2)
supabase/migrations/*.sql
```

### 3.10 Phase 1 acceptance criteria
- [ ] A user can register, log in and log out. They cannot see another user's evidence (RLS tested).
- [ ] Image, audio, PDF and WhatsApp `.zip` uploads all work. The real MIME type is detected.
- [ ] The server computes SHA-256, SHA-1 and MD5. The browser and server SHA-256 match for an unchanged file.
- [ ] Device and identifier fields work. IMEI is validated with the Luhn check.
- [ ] The generated PDF contains Part A, Part B and the Hash Report, with Schedule wording matching Section 2.3 exactly (unit test compares it with the constants).
- [ ] Dates appear as `DD/MM/YYYY` and times as `HH:MM` IST in 24-hour format.
- [ ] Every action listed in 3.4 creates an audit event. UPDATE and DELETE on `audit_events` fail. The hash-chain verifier passes.
- [ ] Finalised certificate versions are read-only, and their `pdf_sha256` is stored.

### 3.11 Out of scope for Phase 1 (design for it, don't build it)
- Razorpay payment per certificate (`lib/billing`)
- An expert account role that receives Part B requests and fills them in their own login
- Aadhaar eSign or DSC digital signing of the PDF
- `ffprobe` video analysis, `.eml` email parsing, CCTV/DVR export guidance
- Multi-language (Hindi) certificate rendering
- Data-retention policy and DPDP Act 2023 consent and notice flows (needed before any commercial launch)

### 3.12 Environment variables
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
MAX_UPLOAD_MB=50
APP_NAME="Section 63 Draft Certificate Tool"
```

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
