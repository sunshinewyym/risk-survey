import csv
from io import BytesIO, StringIO

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font


def export_table(queryset):
    submissions = list(
        queryset.select_related("survey").prefetch_related("answers__question")
    )
    columns = {}
    for submission in submissions:
        for answer in submission.answers.all():
            key = str(answer.question_id)
            columns.setdefault(
                key,
                f"{submission.survey.title}｜{answer.question.order}. {answer.question_label}",
            )
    headers = ["提交编号", "问卷", "提交时间", *columns.values()]
    rows = []
    for submission in submissions:
        answers = {str(answer.question_id): answer.display_value for answer in submission.answers.all()}
        rows.append(
            [
                str(submission.id),
                submission.survey.title,
                timezone.localtime(submission.submitted_at).strftime("%Y-%m-%d %H:%M:%S"),
                *[answers.get(key, "") for key in columns],
            ]
        )
    return headers, rows


def csv_response(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="survey-submissions.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    headers, rows = export_table(queryset)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def xlsx_response(queryset):
    headers, rows = export_table(queryset)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "客户提交"
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        width = min(50, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
        sheet.column_dimensions[column[0].column_letter].width = width
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="survey-submissions.xlsx"'
    return response


def markdown_response(queryset):
    submissions = list(
        queryset.select_related("survey").prefetch_related("answers__question")
    )
    output = StringIO()
    output.write("# 客户问卷提交记录\n\n")
    for submission in submissions:
        submitted_at = timezone.localtime(submission.submitted_at).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        output.write(f"## {submission.survey.title}\n\n")
        output.write(f"- 提交编号：{submission.id}\n")
        output.write(f"- 提交时间：{submitted_at}\n\n")
        for answer in submission.answers.all():
            value = answer.display_value.replace("\r\n", "\n").replace("\r", "\n")
            if "\n" in value:
                output.write(f"### {answer.question.order}. {answer.question_label}\n\n")
                output.write(f"{value}\n\n")
            else:
                output.write(
                    f"- **{answer.question.order}. {answer.question_label}：** "
                    f"{value or '（未填写）'}\n"
                )
        output.write("\n---\n\n")

    response = HttpResponse(output.getvalue(), content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="survey-submissions.md"'
    return response
