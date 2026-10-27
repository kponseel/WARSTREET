import type { MessageKey } from './en'

export const fr: Record<MessageKey, string> = {
  'app.tagline': 'Jeu de bourse fantasy et de guerre entre amis, chaque semaine.',
  'header.language': 'Langue',
  'language.en': 'English',
  'language.fr': 'Français',
  'home.title': 'Bienvenue sur {game}',
  'home.intro':
    'Recrutez 5 vraies actions européennes et américaines chaque week-end, attaquez vos rivaux avec des ordres en milieu de semaine et grimpez au classement chaque vendredi soir.',
  'home.comingSoon': 'Le front est en construction. Les ligues ouvrent bientôt.',
  'home.backend.ok': 'Connexion au serveur configurée.',
  'home.backend.missing': 'Connexion au serveur pas encore configurée.',
  'notFound.title': 'Page introuvable',
  'notFound.back': "Retour à l'accueil",
  // RPC error codes (supabase/migrations, private.raise_error). Variables come from the server.
  'error.unknown': 'Un problème est survenu. Réessayez.',
  'error.ALREADY_MEMBER': 'Vous êtes déjà dans cette ligue.',
  'error.ATTACK_CAP_REACHED': 'Ce joueur a déjà reçu {max} attaques cette semaine.',
  'error.AVATAR_COLOR_INVALID': 'Choisissez une des couleurs proposées.',
  'error.BLOCKADED': 'Vous êtes sous Blocus : ni échange ni ordre de ravitaillement cette semaine.',
  'error.BRIEFING_CLOSED': 'Le briefing est terminé.',
  'error.CAMPAIGN_WEEKS_RANGE': 'Une campagne dure de {min} à {max} semaines.',
  'error.COMMANDER_FORBIDS_ORDER': 'Votre commandant ne peut pas jouer cet ordre.',
  'error.COMMANDER_REQUIRED': 'Choisissez un commandant.',
  'error.CONFLICT_ZONE_NOT_READY':
    "La Zone de conflit de la semaine n'est pas encore prête. Réessayez plus tard.",
  'error.FRONT_NEEDS_REGION':
    'Votre front doit compter au moins {min} unités {region} (actuellement {count}).',
  'error.INVALID_TARGET': 'Ce joueur ne peut pas être ciblé.',
  'error.LEAGUE_FULL': 'Cette ligue est complète ({max} joueurs).',
  'error.LEAGUE_NAME_LENGTH': 'Le nom de la ligue doit faire de 1 à {max} caractères.',
  'error.LEAGUE_NOT_ACTIVE': "Cette ligue n'a pas commencé.",
  'error.LEAGUE_NOT_FOUND': 'Aucune ligue avec ce code.',
  'error.LEAGUE_NOT_IN_LOBBY': 'Cette ligue a déjà commencé.',
  'error.LOCALE_INVALID': 'Langue inconnue.',
  'error.MAX_PLAYERS_RANGE': 'Une ligue compte de {min} à {max} joueurs.',
  'error.NOT_AUTHENTICATED': 'Reconnectez-vous.',
  'error.NOT_A_MEMBER': 'Vous ne faites pas partie de cette ligue.',
  'error.NOT_ENOUGH_AMMO': 'Pas assez de munitions : cet ordre coûte {cost}, vous avez {balance}.',
  'error.NOT_ENOUGH_READY': '{ready} joueurs prêts, il en faut {min} pour lancer.',
  'error.NOT_HOST': "Seul l'hôte peut faire cela.",
  'error.NOT_PACT_PARTNER': 'Seul le joueur invité peut répondre à ce pacte.',
  'error.NO_SQUAD': "Vous n'avez pas d'escouade cette semaine.",
  'error.NO_SUCH_SWAP': 'Aucun échange sur ce poste.',
  'error.ORDER_INVALID': 'Ordre inconnu.',
  'error.ORDER_ONCE_PER_WEEK': "Cet ordre ne peut être joué qu'une fois par semaine.",
  'error.ORDER_WINDOW_CLOSED': 'Les ordres sont fermés pour le moment.',
  'error.ORDER_WRONG_WINDOW': 'Cet ordre ne peut pas être joué pendant cette phase.',
  'error.PACT_ALREADY_ACTIVE': "L'un de vous a déjà un pacte cette semaine.",
  'error.PACT_ALREADY_PROPOSED': 'Un pacte entre vous attend déjà une réponse.',
  'error.PACT_NOT_FOUND': "Ce pacte n'existe plus.",
  'error.PACT_NOT_PENDING': 'Ce pacte a déjà reçu une réponse.',
  'error.PRIORITY_TARGET_NOT_IN_ZONE':
    'La Cible prioritaire doit être dans la Zone de conflit de la semaine.',
  'error.PSEUDO_INVALID': 'Ce nom contient des caractères non autorisés.',
  'error.PSEUDO_LENGTH': 'Votre nom doit faire de {min} à {max} caractères.',
  'error.PSEUDO_RESERVED': 'Ce nom est réservé.',
  'error.PSEUDO_TAKEN': 'Ce nom est déjà pris dans la ligue.',
  'error.RESERVE_ALREADY_USED': 'Cette unité de réserve est déjà utilisée par un autre échange.',
  'error.RESERVE_NEEDS_REGION': 'Votre réserve doit compter au moins {min} unité {region}.',
  'error.RESERVE_SLOT_EMPTY': 'Aucune unité de réserve à ce poste.',
  'error.RESUPPLY_CLOSED': 'Le ravitaillement est fermé.',
  'error.SQUAD_DUPLICATE_INSTRUMENT':
    "Une action ne peut apparaître qu'une fois dans votre escouade.",
  'error.SQUAD_INVALID': 'Cette escouade est illisible.',
  'error.SQUAD_MISSING_SLOT': 'Il manque une unité ({slot}).',
  'error.SQUAD_UNKNOWN_SLOT': 'Poste inconnu ({slot}).',
  'error.SWAP_INVALID_SLOT': 'Seule une unité du front peut être échangée.',
  'error.SWAP_LIMIT': 'Vous pouvez faire {max} échange(s) cette semaine.',
  'error.TARGET_IMMUNE_TO_INTEL': "L'Ombre ne peut pas être ciblée par Renseignement.",
  'error.TARGET_NOT_ALLOWED': 'Cet ordre ne vise pas de joueur.',
  'error.TARGET_REQUIRED': 'Choisissez une cible.',
  'error.TARGET_SLOT_INVALID': 'Cette unité ne peut pas être choisie pour cet ordre.',
  'error.TARGET_SLOT_NOT_ALLOWED': "Cet ordre ne vise pas d'unité.",
  'error.TARGET_SLOT_REQUIRED': 'Choisissez une unité.',
  'error.UNKNOWN_INSTRUMENT': 'Action inconnue ({slot}).',
  'error.VETERAN_SAME_REGION': "Votre Vétéran doit venir d'une autre région que votre Champion.",
  // Front Dispatch (jobs/dispatch.py): template_key + '.' + variant; same variant in EN and FR.
  'dispatch.monday.0':
    'Communiqué du Front, lundi : premiers tirs. {mover} ouvre les hostilités à {move} %. {leader} prend la tête avec {pf} PF.',
  'dispatch.monday.1':
    "Rapport de l'aube : {mover} a bougé de {move} % avant la fin du café. Premier maître du terrain : {leader} ({pf} PF).",
  'dispatch.monday.2':
    'Les marchés se réveillent et {mover} est déjà à {move} %. {leader} plante le drapeau le premier : {pf} PF.',
  'dispatch.monday_fog.0':
    'Communiqué du Front, lundi : {mover} ouvre à {move} %. Le brouillard de guerre cache le meneur.',
  'dispatch.monday_fog.1':
    "Rapport de l'aube : {mover} a bougé de {move} %. Aucun meneur visible : quelqu'un se cache.",
  'dispatch.monday_fog.2':
    '{mover} démarre la semaine à {move} %. Le classement est noyé dans la fumée.',
  'dispatch.thursday.0':
    'Bilan du ravitaillement : {swaps} échange(s), {attacks} attaque(s) réussie(s), {blocked} bloquée(s) par un champ de force, {pacts} pacte(s) en vigueur.',
  'dispatch.thursday.1':
    'Convoi du jeudi : {swaps} unité(s) relevée(s), {attacks} tir(s) au but, {blocked} tir(s) déviés, {pacts} alliance(s) sur la carte.',
  'dispatch.thursday.2':
    'Renseignement de mi-semaine : {attacks} frappe(s) passée(s), {blocked} arrêtée(s) par un bouclier, {swaps} échange(s) au dépôt, {pacts} pacte(s) signé(s).',
  'dispatch.debrief.0':
    'Bilan : {winner} remporte la semaine avec {pf} PF. Unité héroïque : {best} ({best_move} %). Perte de la semaine : {worst} ({worst_move} %). Le Drone a marqué {drone_pf} PF et rouillé {rusty} commandant(s).',
  'dispatch.debrief.1':
    "Vendredi soir, la fumée se dissipe : {winner} tient la colline avec {pf} PF. {best} a porté l'escouade ({best_move} %), {worst} a coulé ({worst_move} %). Drone : {drone_pf} PF, {rusty} joueur(s) battu(s) par un tirage au sort.",
  'dispatch.debrief.2':
    'Semaine terminée. Médaille pour {winner} ({pf} PF). Meilleure unité {best} à {best_move} %, pire {worst} à {worst_move} %. Les {drone_pf} PF du Drone ont humilié {rusty} commandant(s).',
}
