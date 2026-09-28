// Reads emails that local Supabase delivered to Mailpit (supabase/config.toml [inbucket]).
const MAILPIT_URL = process.env.E2E_MAILPIT_URL ?? "http://127.0.0.1:54324";

type Summary = { ID: string; To: { Address: string }[] };

/** The first link in the newest email to `address`, waiting up to 10 s for it to arrive. */
export async function latestLinkTo(address: string): Promise<string> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const list = (await (await fetch(`${MAILPIT_URL}/api/v1/messages`)).json()) as {
      messages: Summary[];
    };
    const summary = list.messages.find((message) =>
      message.To.some((to) => to.Address === address),
    );
    if (summary) {
      const message = (await (
        await fetch(`${MAILPIT_URL}/api/v1/message/${summary.ID}`)
      ).json()) as { Text: string };
      const link = message.Text.match(/https?:\/\/[^\s)]+/)?.[0];
      if (link) return link;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`No email reached ${address}`);
}
