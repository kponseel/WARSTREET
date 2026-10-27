// Reference language. Every key must also exist in fr.ts (enforced by the type and a test).
// Variables use {name} placeholders.
export const en = {
  'app.tagline': 'Weekly fantasy stock-market war game for friends.',
  'header.language': 'Language',
  'language.en': 'English',
  'language.fr': 'Français',
  'home.title': 'Welcome to {game}',
  'home.intro':
    'Draft 5 real EU and US stocks every weekend, attack your rivals with orders mid-week and climb the leaderboard every Friday night.',
  'home.comingSoon': 'The front is being built. Leagues open soon.',
  'home.backend.ok': 'Server connection configured.',
  'home.backend.missing': 'Server connection not configured yet.',
  'notFound.title': 'Page not found',
  'notFound.back': 'Back to home',
  // RPC error codes (supabase/migrations, private.raise_error). Variables come from the server.
  'error.unknown': 'Something went wrong. Please try again.',
  'error.ALREADY_MEMBER': 'You are already in this league.',
  'error.ATTACK_CAP_REACHED': 'This player has already received {max} attacks this week.',
  'error.AVATAR_COLOR_INVALID': 'Pick one of the proposed colours.',
  'error.BLOCKADED': 'You are under Blockade: no swap and no resupply order this week.',
  'error.BRIEFING_CLOSED': 'The briefing is closed.',
  'error.CAMPAIGN_WEEKS_RANGE': 'A campaign lasts {min} to {max} weeks.',
  'error.COMMANDER_FORBIDS_ORDER': 'Your commander cannot play this order.',
  'error.COMMANDER_REQUIRED': 'Choose a commander.',
  'error.CONFLICT_ZONE_NOT_READY': "This week's Conflict Zone is not ready yet. Try again later.",
  'error.FRONT_NEEDS_REGION': 'Your front needs at least {min} {region} units (now {count}).',
  'error.INVALID_TARGET': 'This player cannot be targeted.',
  'error.LEAGUE_FULL': 'This league is full ({max} players).',
  'error.LEAGUE_NAME_LENGTH': 'The league name must be 1 to {max} characters.',
  'error.LEAGUE_NOT_ACTIVE': 'This league has not started.',
  'error.LEAGUE_NOT_FOUND': 'No league with this code.',
  'error.LEAGUE_NOT_IN_LOBBY': 'This league has already started.',
  'error.LOCALE_INVALID': 'Unknown language.',
  'error.MAX_PLAYERS_RANGE': 'A league has {min} to {max} players.',
  'error.NOT_AUTHENTICATED': 'Please log in again.',
  'error.NOT_A_MEMBER': 'You are not a member of this league.',
  'error.NOT_ENOUGH_AMMO': 'Not enough ammo: this order costs {cost}, you have {balance}.',
  'error.NOT_ENOUGH_READY': '{ready} players ready, {min} needed to start.',
  'error.NOT_HOST': 'Only the host can do this.',
  'error.NOT_PACT_PARTNER': 'Only the invited player can answer this pact.',
  'error.NO_SQUAD': 'You have no squad this week.',
  'error.NO_SUCH_SWAP': 'There is no swap on this slot.',
  'error.ORDER_INVALID': 'Unknown order.',
  'error.ORDER_ONCE_PER_WEEK': 'This order can be played once per week.',
  'error.ORDER_WINDOW_CLOSED': 'Orders are closed right now.',
  'error.ORDER_WRONG_WINDOW': 'This order cannot be played during this phase.',
  'error.PACT_ALREADY_ACTIVE': 'One of you already has a pact this week.',
  'error.PACT_ALREADY_PROPOSED': 'A pact between you is already waiting for an answer.',
  'error.PACT_NOT_FOUND': 'This pact no longer exists.',
  'error.PACT_NOT_PENDING': 'This pact has already been answered.',
  'error.PRIORITY_TARGET_NOT_IN_ZONE': "The Priority Target must be in this week's Conflict Zone.",
  'error.PSEUDO_INVALID': 'This name contains characters that are not allowed.',
  'error.PSEUDO_LENGTH': 'Your name must be {min} to {max} characters.',
  'error.PSEUDO_RESERVED': 'This name is reserved.',
  'error.PSEUDO_TAKEN': 'This name is already taken in the league.',
  'error.RESERVE_ALREADY_USED': 'This reserve unit is already used by another swap.',
  'error.RESERVE_NEEDS_REGION': 'Your reserve needs at least {min} {region} unit.',
  'error.RESERVE_SLOT_EMPTY': 'There is no reserve unit in this slot.',
  'error.RESUPPLY_CLOSED': 'Resupply is closed.',
  'error.SQUAD_DUPLICATE_INSTRUMENT': 'A stock can appear only once in your squad.',
  'error.SQUAD_INVALID': 'This squad could not be read.',
  'error.SQUAD_MISSING_SLOT': 'A unit is missing ({slot}).',
  'error.SQUAD_UNKNOWN_SLOT': 'Unknown slot ({slot}).',
  'error.SWAP_INVALID_SLOT': 'Only a front unit can be swapped.',
  'error.SWAP_LIMIT': 'You can make {max} swap(s) this week.',
  'error.TARGET_IMMUNE_TO_INTEL': 'The Shadow cannot be targeted by Intel.',
  'error.TARGET_NOT_ALLOWED': 'This order does not target a player.',
  'error.TARGET_REQUIRED': 'Choose a target.',
  'error.TARGET_SLOT_INVALID': 'This unit cannot be chosen for this order.',
  'error.TARGET_SLOT_NOT_ALLOWED': 'This order does not target a unit.',
  'error.TARGET_SLOT_REQUIRED': 'Choose a unit.',
  'error.UNKNOWN_INSTRUMENT': 'Unknown stock ({slot}).',
  'error.VETERAN_SAME_REGION': 'Your Veteran must come from a different region than your Champion.',
  // Front Dispatch (jobs/dispatch.py): template_key + '.' + variant; same variant in EN and FR.
  'dispatch.monday.0':
    'Front Dispatch, Monday: first shots fired. {mover} opens the war at {move} %. {leader} takes the early lead with {pf} FP.',
  'dispatch.monday.1':
    'Dawn report: {mover} moved {move} % before the coffee was cold. Early commander of the field: {leader} ({pf} FP).',
  'dispatch.monday.2':
    'The markets wake up and {mover} is already at {move} %. {leader} plants the flag first: {pf} FP.',
  'dispatch.monday_fog.0':
    'Front Dispatch, Monday: {mover} opens at {move} %. The fog of war hides the leader.',
  'dispatch.monday_fog.1':
    'Dawn report: {mover} moved {move} %. No visible leader yet: someone is hiding.',
  'dispatch.monday_fog.2':
    '{mover} starts the week at {move} %. The leaderboard is jammed in smoke.',
  'dispatch.thursday.0':
    'Resupply recap: {swaps} swap(s), {attacks} attack(s) landed, {blocked} blocked by force fields, {pacts} pact(s) holding.',
  'dispatch.thursday.1':
    'Thursday convoy: {swaps} unit(s) rotated, {attacks} hit(s) confirmed, {blocked} shot(s) deflected, {pacts} alliance(s) on the map.',
  'dispatch.thursday.2':
    'Mid-week intel: {attacks} strike(s) went through, {blocked} bounced off a shield, {swaps} swap(s) at the depot, {pacts} pact(s) signed.',
  'dispatch.debrief.0':
    'Debrief: {winner} wins the week with {pf} FP. Hero unit: {best} ({best_move} %). Casualty of the week: {worst} ({worst_move} %). The Drone scored {drone_pf} and rusted {rusty} commander(s).',
  'dispatch.debrief.1':
    'Friday night, the smoke clears: {winner} holds the hill with {pf} FP. {best} carried the squad ({best_move} %), {worst} sank ({worst_move} %). Drone: {drone_pf} FP, {rusty} player(s) beaten by a random draft.',
  'dispatch.debrief.2':
    "Week over. Medal to {winner} ({pf} FP). Best unit {best} at {best_move} %, worst {worst} at {worst_move} %. The Drone's {drone_pf} FP embarrassed {rusty} commander(s).",
} as const satisfies Record<string, string>

export type MessageKey = keyof typeof en
