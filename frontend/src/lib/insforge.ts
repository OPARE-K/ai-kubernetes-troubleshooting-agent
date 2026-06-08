import { createClient } from "@insforge/sdk";

export const insforge = createClient({
  baseUrl:
    process.env.NEXT_PUBLIC_INSFORGE_BASE_URL ??
    "https://35dwg74a.eu-central.insforge.app",
  anonKey: process.env.NEXT_PUBLIC_INSFORGE_ANON_KEY ?? "",
});
