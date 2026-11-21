# Exit-sketch checks

Written **21 November 2026** for invented rooms and routes. See source limits in [RESEARCH.md](RESEARCH.md).

1. Use decision 0103's existing Places and Connections; a renamed or moved room updates the sketch from the same ID. Cupboards/shelves do not become room boxes by default.
2. Two doors from bedroom through the same hallway and same final exit are **not** called two independent exits. A loop or duplicate connection cannot create a false second route.
3. A `Door to outside` with blank target, a balcony target and a shared corridor each ask the household to confirm the destination. None is automatically called safe or outdoors.
4. A sleeping room with no link or one possible path is marked incomplete with exact words. A window is never inferred; a person adds a possible window marker and confirms local suitability.
5. A multi-floor house shows stairs and one floor per section. A purpose-built flat asks for the building plan and does not prescribe leave or stay put from the room graph.
6. Meeting place and help-needs prompts appear before **Ready to print for practice**; a missing answer keeps the print visibly Draft. No disabled person's name or medical detail appears on the general map.
7. At 320 px and with screen reader/keyboard, a full text connection list reaches the same facts as the drawing. Labels are not color-only, and every line links back to its source record.
8. Print A4 and Letter, dark and light: all floors, labels, meeting place, review date and Draft markers fit. Plant invented access-code/private-detail sentinels; none appears on the drawing, text alternative, PDF, helper description or notification.
9. Switch Stock off or delete a room with connections: the map says it cannot show current routes or updates without silently keeping a stale drawing. A restored room uses current IDs/revisions.
