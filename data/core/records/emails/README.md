# Email records (kind `email`, ids in the EV series: EV-0906 … EV-2054)

Each email in the case correspondence is a catalogue record of its own: one message, one catalogue id, one page at
`https://bucklerfamily.estate/catalogue/?id=EV-0906`. Added 10 November 2026 under core schema 0.4.0 (additive: new kind `email`,
new `email` block). No existing record is changed.

## Numbering
One numbering format throughout the catalogue (owner's decision, 10 November 2026): emails continue the EV series after the highest
EV in use (EV-0905), so the messages are EV-0906 onward. New records take the next unused EV id in catalogue-ingestion order; later backfills keep the next id rather than being inserted into historical numbering. The index remains ordered by message date. The two withheld digit strings are skipped as numbers.
Ids are PREFIX-NNNN, padded to at least four digits; past 9999 they simply get longer (EV-10000 … EV-1000000), and existing ids are never
re-padded. Always sort ids by their number, not as text. Ids are never reused.

## Files
- `index.json` — metadata only, one row per record: id, timestamp, direction, correspondent(s), sender as shown, subject line, thread, whether
  the transcript is public, the part that holds the record, attachment count, message id, linked EV request record, redaction count, headers only (1 for subject-access correspondence).
  Read-models (the ERP, the email archive) read this.
- `emails-01.json` … `emails-25.json` — the records (core schema), in date order, about 350 KB each (parts 24 and 25 are small additive batches).

## Counts (build of 2026-11-28)
- 1147 records, EV-0906 to EV-2054.
- Part 24 (EV-2046–EV-2050, 14 Nov 2026): five messages recovered from Gmail Spam and moved to Inbox — Cardiff Council FOI acknowledgements FOI26520, FOI26521, FOI26599, FOI26600, and Victorian Society automatic reply on the Tŷ Mawr casework archive enquiry.
- Part 25 (EV-2051–EV-2054, 28 Nov 2026): four preservation-request emails recovered from Sent during the catalogue-wide audit — Treescene (17 Sep), Companies House (10 Oct), BP Legal (16 Oct), and an earlier Loosemores request (26 May). Treescene and the earlier Loosemores email are public-safe extracts; Companies House is verbatim; BP Legal has the sender email address redacted. Original messages and attachments remain in Gmail and are not stored in this repository.
- Five existing sent records (EV-1922, EV-1926, EV-1933, EV-1940 and EV-1947) received public-safe transcripts recovered from Gmail. EV-1922 and EV-1926 are verbatim; EV-1933 is an extract omitting quoted earlier correspondence and a project redirect; EV-1940 and EV-1947 omit a project redirect.
- Earlier batch (2026-11-10): 1138 records, EV-0906 to EV-2045: 1056 from the email archive (with its text) and 82 from the case-mail index that the archive does not hold yet (metadata only, transcript "not yet transcribed").
- Every message is shown. Subject-access correspondence shows its headers only (sender, date, subject line) and no transcript where required. Other transcripts are public. A copy of any original can be requested through the catalogue.
- Redaction: black-blocked passages are the minimum for public display: email addresses, phone numbers, postal addresses, personal data, names of private individuals, the house word list and the two withheld digit strings, plus the mail-client image tags, numbers and phrases the editorial lint rejects. The originals are not published anywhere in this repository; a copy can be requested through the catalogue.

## Dedupe (nothing is catalogued twice)
1. Same mailbox message id (`gm-…`) in more than one source: kept once.
2. Otherwise the same timestamp to the minute, sender and subject (normalised; "Re:"/"Fwd:" removed). Index rows carry no sender, so they
   match on the exact timestamp, correspondent and subject. Separate sends of one letter to different bodies stay separate records.
The second key is stored on each record as `email.dedupe_key`.

## Rules
Additive only: a change to an existing email record goes as a pull request labelled `catalogue-change`.

— Cedwyn editors
