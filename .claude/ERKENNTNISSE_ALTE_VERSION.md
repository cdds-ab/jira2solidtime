# Erkenntnisse aus der alten funktionierenden Version

## Solidtime API Payload für Time Entries

### Korrektes Payload-Format

```json
{
  "member_id": "string (UUID)",
  "project_id": "string (UUID)",
  "start": "2025-10-23T08:00:00Z",
  "end": "2025-10-23T10:00:00Z",
  "duration": 7200,
  "description": "Issue-Key: Description [JiraSync:TempoID]",
  "billable": true
}
```

### Wichtige Details

1. **member_id ist NICHT die User-ID!**
   - Kommt aus `get_user_memberships()` nicht aus `/users/me`
   - Es ist die membership ID für die spezifische Organisation
   - Muss aus Memberships gelesen werden:
     ```python
     memberships = solidtime_client.get_user_memberships()
     for membership in memberships:
         if membership.get("organization", {}).get("id") == organization_id:
             member_id = membership.get("id")  # <-- Diese ID!
             break
     ```

2. **start und end Zeit werden BEIDE benötigt**
   - Nicht nur `start`!
   - Format: ISO datetime mit Z suffix
   - `end` = `start` + duration

3. **duration ist in Sekunden**
   - Nicht in Minuten
   - Sollte mit start/end Zeit konsistent sein

4. **Description Format**
   - Format: `{issue_key}: {description} [JiraSync:{tempo_worklog_id}]`
   - Hilft bei Mapping/Tracking

5. **billable Flag**
   - Sollte aus der Config/Worklog kommen
   - Default: false oder basierend auf Worklog-Eigenschaften

## Solidtime Client Methoden (wichtig)

### get_user_memberships()
- Probiert verschiedene Endpoints aus (Fallback-Strategie)
- Gibt Liste von Memberships zurück
- Membership hat: id, organization.id, etc.

### get_organization_members()
- Holt alle Members der Organisation
- Verschiedene Fallback-Endpoints

### get_projects()
- Gibt Projekte für die Organisation zurück
- Braucht organisation_id

### convert_worklog_to_time_entry()
- Konvertiert ein Worklog zu Time Entry Payload
- Berechnet end_time = start_time + duration
- Handled verschiedene Zeit-Formate

## Fehlerbehandlung

- Die alte Version sendet detaillierte Error-Responses
- 422 = Unprocessable Entity (Payload-Fehler)
- Muss vollständige Response-Body loggen

## Mapping/Tracking

- Alt-Version nutzt Worklog-Mapping System
- Speichert Tempo-Worklog-ID → Solidtime-Entry-ID Zuordnung
- Hilft bei Updates/Deletes

## Wichtige Punkte für Minimal-Version

1. ✅ Implement `get_user_memberships()` in SolidtimeClient
2. ✅ Update `create_time_entry()` um member_id und end Zeit zu nutzen
3. ✅ Fix payload format mit allen erforderlichen Feldern
4. ✅ Bessere Error-Logging
5. ✅ Description Format für Tracking
