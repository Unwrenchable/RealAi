import { useEffect, useState } from "react";
import { fetchWorldstate } from "../lib/overseer-client";

export default function OverseerTerminal() {
  const [worldstate, setWorldstate] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWorldstate()
      .then(setWorldstate)
      .catch(err => setError(err.message));
  }, []);

  if (error) return <div className="pipboy-screen">OVERSEER ERROR: {error}</div>;
  if (!worldstate) return <div className="pipboy-screen">CONTACTING OVERSEER...</div>;

  return (
    <div className="pipboy-screen">
      <h2>VAULT 77 OVERSEER LINK</h2>
      <pre>{JSON.stringify(worldstate, null, 2)}</pre>
    </div>
  );
}
