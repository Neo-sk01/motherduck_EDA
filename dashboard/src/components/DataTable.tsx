import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState } from "react";
import { downloadCsv, toCsv } from "../utils/exportCsv";
import { ExportButton } from "./ExportButton";

export interface DataColumn<T extends Record<string, unknown>> {
  key: string;
  header: string;
  align?: "left" | "right";
  value: (row: T) => string | number;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T extends Record<string, unknown>> {
  title: string;
  description?: string;
  rows: T[];
  columns: Array<DataColumn<T>>;
  filename: string;
  headerAction?: React.ReactNode;
}

export function DataTable<T extends Record<string, unknown>>({
  title,
  description = "Sorted by visible table controls.",
  rows,
  columns,
  filename,
  headerAction,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState(columns[columns.length - 1]?.key ?? "");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const sortedRows = useMemo(() => {
    const column = columns.find((candidate) => candidate.key === sortKey) ?? columns[0];
    return [...rows].sort((a, b) => {
      const aValue = column.value(a);
      const bValue = column.value(b);
      const result =
        typeof aValue === "number" && typeof bValue === "number"
          ? aValue - bValue
          : String(aValue).localeCompare(String(bValue));
      return direction === "asc" ? result : -result;
    });
  }, [columns, direction, rows, sortKey]);

  function setSort(columnKey: string) {
    if (columnKey === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(columnKey);
      setDirection("desc");
    }
  }

  function exportRows() {
    const csvRows = sortedRows.map((row) =>
      Object.fromEntries(columns.map((column) => [column.key, column.value(row)])),
    );
    const csv = toCsv(
      csvRows,
      columns.map((column) => ({
        key: column.key,
        header: column.header,
      })),
    );
    downloadCsv(filename, csv);
  }

  return (
    <section className="data-table-wrap">
      <div className="frame-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        {headerAction}
        <ExportButton label={`Export ${title} CSV`} onClick={exportRows} />
      </div>
      <div className="table-scroller">
        <table aria-label={title}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={column.align === "right" ? "numeric" : undefined}>
                  <button type="button" onClick={() => setSort(column.key)}>
                    {column.header}
                    {sortKey === column.key ? (
                      direction === "asc" ? (
                        <ArrowUp aria-hidden="true" size={13} />
                      ) : (
                        <ArrowDown aria-hidden="true" size={13} />
                      )
                    ) : null}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, rowIndex) => (
              <tr key={`${title}-${rowIndex}`}>
                {columns.map((column) => (
                  <td key={column.key} className={column.align === "right" ? "numeric" : undefined}>
                    {column.render ? column.render(row) : column.value(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
