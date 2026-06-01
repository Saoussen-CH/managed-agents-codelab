import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig, getInfo, uploadSkillToGcs, removeSkillFromGcs } from "../api";

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
  const [removeMsg, setRemoveMsg] = useState("");

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

  const uploadGcsMutation = useMutation({
    mutationFn: uploadSkillToGcs,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  const removeGcsMutation = useMutation({
    mutationFn: removeSkillFromGcs,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
      setRemoveMsg("Skill removed from GCS.");
      setTimeout(() => setRemoveMsg(""), 3000);
    },
  });

  const isVertex = info?.surface === "vertex";
  const gcsPath = config?.gcs_skill_path;

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

      {/* GCS Upload — Vertex mode only */}
      {isVertex && (
        <div className="border rounded-xl p-4 space-y-3 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-800">Upload to GCS</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Store SKILL.md in Google Cloud Storage so the agent loads it from GCS instead of inline.
              </p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              gcsPath ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
            }`}>
              {gcsPath ? "Uploaded" : "Not uploaded"}
            </span>
          </div>

          {gcsPath && (
            <p className="text-xs font-mono text-gray-500 break-all bg-gray-50 rounded p-2">
              {gcsPath}
            </p>
          )}

          {uploadGcsMutation.isError && (
            <p className="text-xs text-red-500">
              {uploadGcsMutation.error instanceof Error
                ? uploadGcsMutation.error.message
                : String(uploadGcsMutation.error ?? "Upload failed")}
            </p>
          )}
          {removeGcsMutation.isError && (
            <p className="text-xs text-red-500">
              {removeGcsMutation.error instanceof Error
                ? removeGcsMutation.error.message
                : String(removeGcsMutation.error ?? "Remove failed")}
            </p>
          )}
          {removeMsg && <p className="text-xs text-green-600">{removeMsg}</p>}

          <div className="flex gap-2">
            <button
              onClick={() => uploadGcsMutation.mutate()}
              disabled={uploadGcsMutation.isPending}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
            >
              {uploadGcsMutation.isPending
                ? "Uploading…"
                : gcsPath ? "Re-upload to GCS" : "Upload to GCS"}
            </button>
            {gcsPath && (
              <button
                onClick={() => removeGcsMutation.mutate()}
                disabled={removeGcsMutation.isPending}
                className="text-sm text-red-400 hover:text-red-600 px-3 py-2 transition-colors"
              >
                {removeGcsMutation.isPending ? "…" : "Remove"}
              </button>
            )}
          </div>

          <p className="text-xs text-gray-400">
            Save your skill content first, then upload. Agents created after uploading will load the skill from GCS instead of passing it inline on every call.
          </p>
        </div>
      )}
    </div>
  );
}
