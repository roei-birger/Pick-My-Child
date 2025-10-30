# Feature Flags

## ENABLE_EVENTS_FEATURE

**Default:** `false`

**Description:** Controls whether event-related features are visible in the UI.

### When Disabled (false):
- ❌ "יצירת אירוע (העלאת ZIP)" button is hidden from main menu
- ❌ "יש לי מספר אירוע" button is hidden from main menu
- ✅ All event handlers remain functional (for future use)
- ✅ Database schema includes events tables
- ✅ Event processing code is available but not exposed to users

### When Enabled (true):
- ✅ Full event creation and management UI is available
- ✅ Users can upload ZIP files to create events
- ✅ Users can enter event codes to view filtered photos

### How to Enable:

Add to your `.env` file:
```bash
ENABLE_EVENTS_FEATURE=true
```

Then restart the bot.

---

## Future Feature Flags

As the project grows, you can add more feature flags here:
- `ENABLE_ADMIN_PANEL` - Admin dashboard
- `ENABLE_ANALYTICS` - Usage statistics
- `ENABLE_PAYMENTS` - Premium features
- etc.
