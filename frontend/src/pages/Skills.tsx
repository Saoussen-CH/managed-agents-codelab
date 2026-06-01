import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig, getInfo, publishSkill, unpublishSkill } from "../api";

function parseFrontmatter(md: string) {
  const match = md.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { name: "", description: "", body: md };
  const fm = match[1];
  const body = match[2].trim();
  const name = (fm.match(/^name:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  const description = (fm.match(/^description:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  return { name, description, body };
}

function buildFrontmatter(name: string, description: string, body: string) {
  const safeName = name.replace(/[\r\n]/g, " ").trim();
  const safeDesc = description.replace(/[\r\n]/g, " ").trim();
  return `---\nname: ${safeName}\ndescription: ${safeDesc}\n---\n\n${body}`;
}

export default function Skills() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const { data: info } = useQuery({ queryKey: ["info"], queryFn: getInfo });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [body, setBody] = useState("");
  const [initialised, setInitialised] = useState(false);

  useEffect(() => {
    if (config && !initialised) {
      const p = parseFrontmatter(config.skill_md);
      setName(p.name);
      setDescription(p.description);
      setBody(p.body);
      setInitialised(true);
    }
  }, [config, initialised]);

  const saveMutation = useMutation({
    mutationFn: () => updateConfig({ skill_md: buildFrontmatter(name, description, body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  const publishMutation = useMutation({
    mutationFn: publishSkill,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  const [unpublishDone, setUnpublishDone] = useState(false);

  const unpublishMutation = useMutation({
    mutationFn: unpublishSkill,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
      setUnpublishDone(true);
      setTimeout(() => setUnpublishDone(false), 3000);
    },
  });

  const isVertex = info?.surface === "vertex";
  const registryName = config?.skill_registry_name;

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Skills</h1>
      <p className="text-sm text-gray-500">The SKILL.md that tells the agent how to build the PDF.</p>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            placeholder="digest-pdf"
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Convert a tech news digest into a clean PDF."
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={14}
        placeholder="# Digest PDF Skill&#10;&#10;When the user asks for a PDF..."
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-y"
      />

      <div className="flex justify-end">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {saveMutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>

      {/* Skill Registry — Vertex mode only. Feature may not be available on all projects (Pre-GA enrollment required). */}
      {isVertex && (
        <div className="border rounded-xl p-4 space-y-3 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-800">Skill Registry</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Publish to Vertex AI Skill Registry for proper Vertex-native skill discovery.
              </p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              registryName ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
            }`}>
              {registryName ? "Published" : "Not published"}
            </span>
          </div>

          {registryName && (
            <p className="text-xs font-mono text-gray-500 break-all bg-gray-50 rounded p-2">
              {registryName}
            </p>
          )}

          {publishMutation.isError && (
            <p className="text-xs text-red-500">
              {publishMutation.error instanceof Error
                ? publishMutation.error.message
                : String(publishMutation.error ?? "Publish failed")}
            </p>
          )}
          {unpublishMutation.isError && (
            <p className="text-xs text-red-500">
              {unpublishMutation.error instanceof Error
                ? unpublishMutation.error.message
                : String(unpublishMutation.error ?? "Unpublish failed")}
            </p>
          )}
          {unpublishDone && (
            <p className="text-xs text-green-600">Skill removed from registry.</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
            >
              {publishMutation.isPending
                ? "Publishing… (may take ~30s)"
                : registryName
                ? "Re-publish"
                : "Publish to Registry"}
            </button>
            {registryName && (
              <button
                onClick={() => unpublishMutation.mutate()}
                disabled={unpublishMutation.isPending}
                className="text-sm text-red-400 hover:text-red-600 px-3 py-2 transition-colors"
              >
                {unpublishMutation.isPending ? "…" : "Unpublish"}
              </button>
            )}
          </div>

          <p className="text-xs text-gray-400">
            Save your skill content first, then publish. Agents created after publishing will use the registry skill instead of inline content.
            {" "}If you see a "project doesn't exist" error, the Skill Registry requires separate Pre-GA enrollment — inline skills work identically without it.
          </p>
        </div>
      )}
    </div>
  );
}
