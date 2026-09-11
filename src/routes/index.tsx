import { createFileRoute } from "@tanstack/react-router";
import { ConsoleApp } from "@/components/console/ConsoleApp";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <ConsoleApp />;
}
