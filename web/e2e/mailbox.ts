// The local Supabase mailbox (Mailpit, `supabase start`): reads the latest login email.
const MAILPIT = process.env.MAILPIT_URL ?? 'http://127.0.0.1:54324'

interface MessageList {
  messages?: { ID: string }[]
}

interface Message {
  HTML?: string
  Text?: string
}

async function latestEmail(email: string, timeoutMs: number): Promise<string> {
  const deadline = Date.now() + timeoutMs
  const query = encodeURIComponent(`to:"${email}"`)
  while (Date.now() < deadline) {
    const list = (await (await fetch(`${MAILPIT}/api/v1/search?query=${query}`)).json()) as MessageList
    const latest = list.messages?.[0]
    if (latest) {
      const message = (await (await fetch(`${MAILPIT}/api/v1/message/${latest.ID}`)).json()) as Message
      return `${message.HTML ?? ''}\n${message.Text ?? ''}`
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`no login email for ${email}`)
}

export async function loginCode(email: string, timeoutMs = 30_000): Promise<string> {
  const code = /\b(\d{6})\b/.exec(await latestEmail(email, timeoutMs))?.[1]
  if (!code) throw new Error(`no code in the login email for ${email}`)
  return code
}

export async function loginLink(email: string, timeoutMs = 30_000): Promise<string> {
  const href = /href="([^"]+)"/.exec(await latestEmail(email, timeoutMs))?.[1]
  if (!href) throw new Error(`no link in the login email for ${email}`)
  return href.replaceAll('&amp;', '&')
}
