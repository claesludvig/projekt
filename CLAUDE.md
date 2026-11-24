# Memory

OBS: repot är publikt. Skriv inga personuppgifter, länkar eller fil-ID:n här.

## Att göra-listor – var de finns

| Område | Källa | Hur Claude hittar den |
|--------|-------|-----------------------|
| **Jobb** | Microsoft To Do, exporteras automatiskt via Power Automate som CSV till OneDrive: `Claude/todo-export.csv` | Microsoft 365-kopplingen saknar To Do-behörighet, så läs filen i stället: `sharepoint_search` (query `*`, fileType `csv`), välj `todo-export.csv`, läs med `read_resource` |
| **Privat, studier, bokprojekt** | Google Tasks, exporteras till Google Drive-arket "Google Tasks – export för Claude" | `search_files` på titeln, ladda ner som `text/csv` (`read_file_content` visar bara ett urval av raderna) |

"Jobb" eller "att göra jobbmässigt" betyder alltså To Do-exporten, inte Google Tasks.

### Format på To Do-exporten
Kolumner: `Lista, Uppgift, Status, Viktighet, Forfallodatum, Slutford, Senast_andrad, Anteckningar, Exporterad`
- Status: `notStarted` / `completed`; Viktighet: `normal` / `high`
- Datum är i UTC. Ett förfallodatum som `2026-11-23T23:00:00` betyder **24/11** svensk tid (vintertid: +1 h, sommartid: +2 h).
- Listor (nov 2026): Jobb, Anläggningsprognosen, Media, Struktur för återkommande analys, Tasks (gammal och mest avklarad).
- Kolla kolumnen `Exporterad` så att du vet hur färsk exporten är.
