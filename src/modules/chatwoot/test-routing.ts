import type { ScopedDb } from "@/lib/tenancy";

export interface EffectiveInboxAgent {
  agentId: bigint;
  primaryAgentId: bigint;
  mode: string;
  enabled: boolean;
  settings: unknown;
  selectedAdditionalAgent: boolean;
}

// Resolve the persona that owns this conversation. Production is intentionally boring: the inbox's
// primary agent always wins. Additional personas are honored only while the primary is in test mode,
// the conversation is activated, and the selected agent is still granted to this inbox.
export async function resolveEffectiveInboxAgentForConversationRow(
  db: ScopedDb,
  inboxId: bigint,
  conversationDbId: bigint | null,
): Promise<EffectiveInboxAgent | null> {
  const inbox = await db.inbox.findUnique({
    where: { id: inboxId },
    select: { tenantId: true, agentId: true },
  });
  if (!inbox?.agentId) return null;
  const primaryAgent = await db.agent.findUnique({
    where: { id: inbox.agentId },
    select: { mode: true, enabled: true, settings: true },
  });
  if (!primaryAgent) return null;
  const primary: EffectiveInboxAgent = {
    agentId: inbox.agentId,
    primaryAgentId: inbox.agentId,
    mode: primaryAgent.mode,
    enabled: primaryAgent.enabled,
    settings: primaryAgent.settings,
    selectedAdditionalAgent: false,
  };
  if (primaryAgent.mode !== "test" || conversationDbId === null) return primary;

  const conversation = await db.conversation.findUnique({
    where: { id: conversationDbId },
    select: { testActivatedAt: true, testAgentId: true },
  });
  if (!conversation?.testActivatedAt || !conversation.testAgentId)
    return primary;

  const grant = await db.inboxTestAgent.findUnique({
    where: {
      tenantId_inboxId_agentId: {
        tenantId: inbox.tenantId,
        inboxId,
        agentId: conversation.testAgentId,
      },
    },
    select: {
      agent: {
        select: { id: true, mode: true, enabled: true, settings: true },
      },
    },
  });
  if (grant?.agent?.mode !== "test") return primary;
  return {
    agentId: grant.agent.id,
    primaryAgentId: inbox.agentId,
    mode: grant.agent.mode,
    enabled: grant.agent.enabled,
    settings: grant.agent.settings,
    selectedAdditionalAgent: true,
  };
}
