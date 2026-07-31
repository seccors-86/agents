-- Additional test personas per inbox. Chatwoot keeps one physical bot connection; the selected
-- persona is routed internally per conversation while the primary agent remains in test mode.
CREATE TABLE "inbox_test_agents" (
    "id" BIGSERIAL NOT NULL,
    "tenant_id" BIGINT NOT NULL,
    "inbox_id" BIGINT NOT NULL,
    "agent_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "inbox_test_agents_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "conversations"
  ADD COLUMN "test_agent_id" BIGINT;

CREATE UNIQUE INDEX "inbox_test_agents_tenant_id_inbox_id_agent_id_key"
  ON "inbox_test_agents"("tenant_id", "inbox_id", "agent_id");
CREATE INDEX "inbox_test_agents_tenant_id_idx"
  ON "inbox_test_agents"("tenant_id");
CREATE INDEX "inbox_test_agents_agent_id_idx"
  ON "inbox_test_agents"("agent_id");
CREATE INDEX "conversations_test_agent_id_idx"
  ON "conversations"("test_agent_id");

ALTER TABLE "inbox_test_agents"
  ADD CONSTRAINT "inbox_test_agents_tenant_id_fkey"
  FOREIGN KEY ("tenant_id") REFERENCES "tenants"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "inbox_test_agents"
  ADD CONSTRAINT "inbox_test_agents_inbox_id_fkey"
  FOREIGN KEY ("inbox_id") REFERENCES "inboxes"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "inbox_test_agents"
  ADD CONSTRAINT "inbox_test_agents_agent_id_fkey"
  FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "conversations"
  ADD CONSTRAINT "conversations_test_agent_id_fkey"
  FOREIGN KEY ("test_agent_id") REFERENCES "agents"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "inbox_test_agents" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "inbox_test_agents" FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON "inbox_test_agents"
  USING (
    current_setting('app.is_super_admin', true) = 'on'
    OR tenant_id = nullif(current_setting('app.tenant_id', true), '')::bigint
  )
  WITH CHECK (
    current_setting('app.is_super_admin', true) = 'on'
    OR tenant_id = nullif(current_setting('app.tenant_id', true), '')::bigint
  );
