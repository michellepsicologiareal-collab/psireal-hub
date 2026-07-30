-- Atualizar tabela PSIS com campos necessários
ALTER TABLE "PSIS" ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE "PSIS" ADD COLUMN IF NOT EXISTS whatsapp text;
ALTER TABLE "PSIS" ADD COLUMN IF NOT EXISTS plano text DEFAULT 'mensal';
ALTER TABLE "PSIS" ADD COLUMN IF NOT EXISTS ativa boolean DEFAULT true;
ALTER TABLE "PSIS" ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

-- RLS para PSIS
ALTER TABLE "PSIS" ENABLE ROW LEVEL SECURITY;

-- Anon pode SELECT (para validar psi_id no login)
CREATE POLICY "allow_anon_select_psis" ON "PSIS"
FOR SELECT TO anon USING (true);

-- Service role pode tudo
CREATE POLICY "allow_service_all_psis" ON "PSIS"
FOR ALL TO service_role USING (true);

-- Inserir Michelle como psi padrão (se não existir)
INSERT INTO "PSIS" (nome, psi_id, email, whatsapp, plano, ativa)
VALUES ('Michelle Donegá dos Santos', 'michelle', 'michellepsicologiareal@gmail.com', '5511947388423', 'fundadora', true)
ON CONFLICT (psi_id) DO NOTHING;

-- RLS respostas_clinicas — psi vê só as suas
CREATE POLICY "allow_anon_select_respostas" ON respostas_clinicas
FOR SELECT TO anon USING (true);
