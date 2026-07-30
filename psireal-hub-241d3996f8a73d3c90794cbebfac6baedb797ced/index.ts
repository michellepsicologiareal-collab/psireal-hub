import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) return json({ error: "missing authorization" }, 401);

  const url = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !anonKey || !serviceRoleKey) return json({ error: "missing environment" }, 500);

  const callerClient = createClient(url, anonKey, { global: { headers: { Authorization: authHeader } } });
  const adminClient = createClient(url, serviceRoleKey);

  const { data: { user }, error: authError } = await callerClient.auth.getUser();
  if (authError || !user) return json({ error: "invalid session" }, 401);

  const { data: adminRow } = await callerClient
    .from("admin_users")
    .select("user_id")
    .eq("user_id", user.id)
    .maybeSingle();
  if (!adminRow) return json({ error: "admin required" }, 403);

  const body = await req.json();
  const email = String(body.email || "").trim().toLowerCase();
  const password = String(body.password || "").trim();
  const nome = String(body.nome || "").trim();
  const psiId = String(body.psi_id || "").trim().toLowerCase();
  const whatsapp = body.whatsapp ? String(body.whatsapp).trim() : null;
  const plano = String(body.plano || "mensal").trim();
  if (!email || !password || !nome || !psiId) return json({ error: "missing fields" }, 400);

  const { data: created, error: createError } = await adminClient.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  if (createError || !created.user) {
    return json({ error: createError?.message || "could not create user" }, 400);
  }

  const { error: insertError } = await adminClient.from("psis").insert({
    user_id: created.user.id,
    psi_id: psiId,
    nome,
    email,
    whatsapp,
    plano,
    ativa: true,
  });
  if (insertError) {
    await adminClient.auth.admin.deleteUser(created.user.id);
    return json({ error: insertError.message }, 400);
  }

  return json({ user_id: created.user.id, email, psi_id: psiId, nome });
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}
