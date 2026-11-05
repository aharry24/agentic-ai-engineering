# Format Negotiation for Multi-Agent (A2A) Communication

When two AI agents exchange messages, they don't always speak the same data format: one might produce XML, another CSV, while a third only reads JSON. This project shows how agents can still communicate reliably. Each agent **declares** the formats it supports, the two **negotiate** a shared format at runtime, the payload is **converted** automatically between **JSON, XML and CSV** when needed, and if there's no common format the system **fails safely** with a clear, auditable log instead of sending something the receiver can't read.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<your-username>/<your-repo>/blob/main/Format_Negotiation_A2A.ipynb)

## How it works

```
 NEGOTIATE ──► CONVERT (only if needed) ──► DELIVER
     │
     └── no common format ──► FALLBACK (abort and log)
```

| Step | What happens |
|---|---|
| **Declare** | Each `Agent` lists the formats it supports (for example `["XML", "JSON"]`) and its preference order |
| **Negotiate** | Find the formats both agents support. If there's more than one, the sender's preference wins, then the receiver's |
| **Convert** | If the sender's payload isn't in the agreed format, decode it into a Python dictionary, then encode it into the agreed format |
| **Deliver** | Send the payload with the right content type (`application/json`, `application/xml` or `text/csv`) |
| **Fallback** | If the two agents share no format, abort and log `no_common_format` |

Every step prints a log line (`NEGOTIATE`, `CONVERT`, `DELIVER`, `FALLBACK`), so each exchange leaves an audit trail.

### Format registry

Each format is defined by an **encoder** (dict → bytes), a **decoder** (bytes → dict) and a content type, stored in one table:

```python
FORMATS = {
    "JSON": (dict_to_json_bytes, json_bytes_to_dict, "application/json"),
    "XML":  (dict_to_xml_bytes,  xml_bytes_to_dict,  "application/xml"),
    "CSV":  (dict_to_csv_bytes,  csv_bytes_to_dict,  "text/csv"),
}
```

Every conversion follows the same path: decode the source into a dict, then encode it into the destination. With three formats, all 9 source → destination pairs work without any pair-specific code. Adding a new format means writing two functions and adding one line to `FORMATS`; the negotiation and agent code don't change.

## Scenarios

| # | Sender supports (prefers) | Receiver supports | Agreed format | Outcome |
|---|---|---|---|---|
| 1 | XML, JSON (XML) | JSON | JSON | ✅ XML converted to JSON, then delivered |
| 2 | XML, JSON (JSON) | XML | XML | ✅ JSON converted to XML, then delivered |
| 3 | XML | JSON | none | ⛔ Safe fallback: aborted and logged |
| 4 | JSON, XML (JSON) | JSON, XML | JSON | ✅ Delivered unchanged, no conversion needed |
| 5 | CSV, JSON (CSV) | JSON | JSON | ✅ CSV converted to JSON, then delivered |
| 6 | XML, CSV (XML) | CSV | CSV | ✅ XML converted to CSV, then delivered |

The notebook ends with automated checks:
- Each scenario returned the expected result.
- **All 9 format pairs** round-trip without losing or changing data. Types survive too: `101` stays an integer and `123.45` stays a float, even through XML and CSV, which store everything as text.
- CSV correctly handles values that contain commas and quotes, such as `Report, "Q4" final`.

## Example output

```
=== Scenario 1: XML -> JSON convert ===
NEGOTIATE: sender=A, receiver=B, sender_supported=['XML', 'JSON'], receiver_supported=['JSON'], agreed=JSON
CONVERT: XML -> JSON
PAYLOAD BEFORE (XML):
<message><id>101</id><title>Quarterly Report</title><amount>123.45</amount></message>
PAYLOAD AFTER (JSON):
{"id":101,"title":"Quarterly Report","amount":123.45}
DELIVER: content_type=application/json, ok=True

=== Scenario 5: CSV -> JSON convert ===
NEGOTIATE: sender=G, receiver=J, sender_supported=['CSV', 'JSON'], receiver_supported=['JSON'], agreed=JSON
CONVERT: CSV -> JSON
PAYLOAD BEFORE (CSV):
id,title,amount
101,Quarterly Report,123.45
PAYLOAD AFTER (JSON):
{"id":101,"title":"Quarterly Report","amount":123.45}
DELIVER: content_type=application/json, ok=True

=== Scenario 3: Fallback (no overlap) ===
NEGOTIATE: sender=C, receiver=D, sender_supported=['XML'], receiver_supported=['JSON'], agreed=None
FALLBACK: No common format. Action=abort_and_log
RESULT: {'ok': False, 'reason': 'no_common_format'}
```

```
Round trips passed for all 9 format pairs
#  Scenario      Delivered  Agreed format  Note
--------------------------------------------------------------
1  XML -> JSON   True       JSON           application/json
2  JSON -> XML   True       XML            application/xml
3  No overlap    False      -              no_common_format
4  Same format   True       JSON           application/json
5  CSV -> JSON   True       JSON           application/json
6  XML -> CSV    True       CSV            text/csv

All checks passed ✅
```

## Run it

There's no API key and nothing to install: the project uses only Python's standard library.

**Google Colab:** open the notebook (use the badge above, or upload `Format_Negotiation_A2A.ipynb`) and choose **Runtime → Run all**.

**Locally, as a script:**

```bash
python format_demo.py
```

**Locally, as a notebook:**

```bash
pip install -r requirements.txt
jupyter notebook Format_Negotiation_A2A.ipynb
```

## Files

| File | Purpose |
|---|---|
| `Format_Negotiation_A2A.ipynb` | Step-by-step notebook with explanations and saved output |
| `format_demo.py` | The same code as a single script that runs all six scenarios and the checks |
| `requirements.txt` | Only needed to run the notebook locally (Jupyter) |

## Known limitations

- **Flat messages only.** The XML and CSV converters handle simple key–value messages. Nested objects and lists would need a richer mapping.
- **One record per CSV message.** Each CSV payload is a header row plus exactly one data row; anything else is rejected with a clear error.
- **XML and CSV values are all text.** When reading them, anything that looks like a number becomes a number. A value meant to stay text, such as a ZIP code like `"02134"`, would be changed to `2134`.
- **The sender's preference wins.** When several formats are shared, the sender's preference comes first. Real systems might let the receiver decide or score the options instead.

## Possible extensions

- Add another format, such as YAML (needs PyYAML) or TOML, by writing one encoder and one decoder and adding it to `FORMATS`
- Support nested data and schema validation
- Return a structured audit log (a list of events) instead of printing it
- Make the negotiation rule configurable (sender first, receiver first, or scored)

## Tech stack

Python standard library: `json`, `xml.etree.ElementTree`, `csv`, `io`, `typing`

## Credits

Based on *Lesson 02, Demo 01: Negotiating Response Format for Multi-Agent Communication* from my Agentic AI coursework. I adapted it for Google Colab and GitHub and made these changes:

- Merged the three separate scenario runs into one notebook
- Added CSV as a third format, with a format registry so any format converts to any other
- Added three more scenarios: no conversion, CSV → JSON and XML → CSV
- Added automated checks, including round-trip tests for all 9 format pairs
- Replaced the bare `except` with specific exception types
- Made the fallback choice of format deterministic
