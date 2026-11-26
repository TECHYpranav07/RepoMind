import { useQuery } from "@tanstack/react-query";
import { useWorkspace } from "./workspace";

function useKey(name: string, ...extra: unknown[]) {
  const { connection, repoVersion } = useWorkspace();
  return [name, connection.mode, connection.url, repoVersion, ...extra];
}

export function useGraphQuery(enabled = true) {
  const { client } = useWorkspace();
  return useQuery({ queryKey: useKey("graph"), queryFn: () => client.getGraph(), enabled, staleTime: Infinity });
}

export function useFilesQuery(enabled = true) {
  const { client } = useWorkspace();
  return useQuery({ queryKey: useKey("files"), queryFn: () => client.listFiles(), enabled, staleTime: Infinity });
}

export function useFileQuery(path: string | null) {
  const { client } = useWorkspace();
  return useQuery({
    queryKey: useKey("file", path),
    queryFn: () => client.getFile(path!),
    enabled: Boolean(path),
    staleTime: Infinity,
  });
}

export function useSuggestionsQuery(enabled = true) {
  const { client } = useWorkspace();
  return useQuery({ queryKey: useKey("suggestions"), queryFn: () => client.chatSuggestions(), enabled, staleTime: Infinity });
}

export function useScenariosQuery(enabled = true) {
  const { client } = useWorkspace();
  return useQuery({ queryKey: useKey("scenarios"), queryFn: () => client.whatifScenarios(), enabled, staleTime: Infinity });
}
