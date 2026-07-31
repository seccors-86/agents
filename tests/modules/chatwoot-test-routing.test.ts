import { describe, expect, test } from "bun:test";
import type { ScopedDb } from "@/lib/tenancy";
import { resolveEffectiveInboxAgentForConversationRow } from "@/modules/chatwoot/test-routing";

function dbFixture(options: {
  primaryMode: "test" | "production";
  activated?: boolean;
  selectedAgentId?: bigint | null;
  granted?: boolean;
}) {
  return {
    inbox: {
      findUnique: async () => ({ tenantId: 1n, agentId: 10n }),
    },
    agent: {
      findUnique: async ({ where }: { where: { id: bigint } }) =>
        where.id === 10n
          ? {
              mode: options.primaryMode,
              enabled: true,
              settings: { persona: "primary" },
            }
          : null,
    },
    conversation: {
      findUnique: async () => ({
        testActivatedAt: options.activated ? new Date() : null,
        testAgentId: options.selectedAgentId ?? null,
      }),
    },
    inboxTestAgent: {
      findUnique: async () =>
        options.granted
          ? {
              agent: {
                id: 20n,
                mode: "test",
                enabled: true,
                settings: { persona: "secondary" },
              },
            }
          : null,
    },
  } as unknown as ScopedDb;
}

describe("multi-agent test routing", () => {
  test("production always uses the single primary agent", async () => {
    const result = await resolveEffectiveInboxAgentForConversationRow(
      dbFixture({
        primaryMode: "production",
        activated: true,
        selectedAgentId: 20n,
        granted: true,
      }),
      100n,
      200n,
    );
    expect(result?.agentId).toBe(10n);
    expect(result?.selectedAdditionalAgent).toBe(false);
  });

  test("an activated conversation may select a granted test agent", async () => {
    const result = await resolveEffectiveInboxAgentForConversationRow(
      dbFixture({
        primaryMode: "test",
        activated: true,
        selectedAgentId: 20n,
        granted: true,
      }),
      100n,
      200n,
    );
    expect(result?.agentId).toBe(20n);
    expect(result?.selectedAdditionalAgent).toBe(true);
    expect(result?.settings).toEqual({ persona: "secondary" });
  });

  test("an ungranted or inactive selection falls back to the primary", async () => {
    const inactive = await resolveEffectiveInboxAgentForConversationRow(
      dbFixture({
        primaryMode: "test",
        activated: false,
        selectedAgentId: 20n,
        granted: true,
      }),
      100n,
      200n,
    );
    const ungranted = await resolveEffectiveInboxAgentForConversationRow(
      dbFixture({
        primaryMode: "test",
        activated: true,
        selectedAgentId: 20n,
        granted: false,
      }),
      100n,
      200n,
    );
    expect(inactive?.agentId).toBe(10n);
    expect(ungranted?.agentId).toBe(10n);
  });
});
