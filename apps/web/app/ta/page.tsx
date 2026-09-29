import { redirect } from "next/navigation";

import { HOME_PATH } from "@/lib/app-nav";

// The app host's root opens Overview.
export default function AppHome() {
  redirect(HOME_PATH);
}
