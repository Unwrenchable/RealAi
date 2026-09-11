import { redirect } from "next/navigation";

/**
 * RealAI single surface: console on the gateway.
 * Next App Router chat shell is merged into http://127.0.0.1:8001/console
 * (Ops dock + Settings + hive/abilities). Do not treat :3000 as a second product.
 */
export default function HomePage() {
  redirect("http://127.0.0.1:8001/console");
}
