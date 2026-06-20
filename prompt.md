Create a structured data table extracting speech units from Israeli government cabinet 
meeting minutes with these exact columns:

RULES FOR EXTRACTION:

Core Rule:
Copy all text and data exactly as they appear in the source document. Do not add, 
correct, interpret, summarize, normalize, translate, or omit anything.

Speaker Recognition:
- Speaker labels appear underlined in original (appears as normal text in OCR)
- Typically formatted as: [Title] [Speaker initials/name]:
  Examples: "ראש הממשלה ל. אשכול:", "שר הדתות ז. ורהפטיג:", "י. גלילי:"
- Can be title alone ("שר המשפטים ימלא מקומו...") or title + name
- Look for Hebrew text followed by colon (:)
- Distinguish from list items, decisions, or quoted material

Speech Unit Boundaries:
- Each row = ONE continuous speech by ONE speaker
- Do NOT merge multiple speakers into one row
- Do NOT split one speaker's continuous speech into multiple rows
- Include multi-page speeches in single row with all page numbers

Topic & Agenda Item Recognition:
- Agenda items numbered: 679, 680, 681... (or .679, .680, .681)
- Followed by Hebrew title (agenda item description)
- Topic continues until next numbered item
- If topic unclear, leave blank rather than guessing

Quality Standards:
- Preserve exact spelling (including errors/typos from original)
- Preserve exact punctuation and abbreviations
- Preserve exact names and titles as they appear
- Do NOT infer missing information
- If page number unclear, leave blank or estimate with "~" (e.g., "~15-20")

OUTPUT FORMAT:
Generate table with all columns. One row per speech unit. Include all rows extracted 
from document, even if some cells are blank. Verify serial numbers are sequential 
(001, 002, 003...) per meeting.

COLUMN DEFINITIONS:
1. Serial Number — Format: YYYYMMDDX_TTT
   - YYYYMMDD = meeting date
   - X = session letter (A=morning/בוקר, B=before-noon/לפני הצהריים, C=noon/צהריים, 
     D=afternoon/אחר הצהריים, E=evening/ערב, F=night/לילה, Z=unknown/לא ידוע)
   - TTT = 3-digit counter (001, 002, 003...), resets per meeting

2. Hebrew Date — Exact Hebrew date from source (e.g., כ"ד באב תשכ"ח). If unknown leave blank. 

3. Date — Gregorian format: DD/MM/YYYY

4. Time — Session start time if stated in source; otherwise blank

5. Speaker — Speaker label exactly as it appears in source document
   (e.g., "ראש הממשלה ל. אשכול", "שר הביטחון מ. דיין", "י. גלילי")

6. Full Name — Full name looked up from government roster
   (e.g., "לוי אשכול", "משה דיין", "יצחק גלילי"). If unknown leave blank.  

7. Role — Ministerial title at time of meeting
   (e.g., "ראש הממשלה", "שר הביטחון", "שר הפנים", "סגן ראש הממשלה"). If unknown leave blank. 

8. Party — Political party at time of meeting
   (Values: המערך, רפ"י, מפ"ם, מפד"ל, גח"ל, ליברלים עצמאיים). If unknown leave blank. 

9. Text Unit — Complete transcribed speech text, exactly as it appears in source
   - Preserve original spelling, punctuation, abbreviations
   - Do NOT correct, summarize, interpret, or normalize

10. Page/s: Use the internal protocol page numbers found in the document headers 
    (Single page: "5", Multiple pages: "5-7"). 

11. Topic — Agenda item title from source

12. Section Number — Agenda item number from source (e.g., 679, 680, 681)
    Leave blank if not clearly stated