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


def registration_export_table(queryset):
    registrations = list(queryset.prefetch_related("attendees"))
    headers = [
        "报名编号",
        "公司名称",
        "联系人",
        "联系电话",
        "城市",
        "参会人数",
        "参会人员",
        "合作项目数量",
        "涉诉/追索数量",
        "重点问题",
        "其他风险",
        "了解渠道",
        "提交时间",
        "飞书通知",
    ]
    rows = []
    for registration in registrations:
        attendees = "；".join(
            f"{person.name} / {person.role} / {person.phone}"
            for person in registration.attendees.all()
        )
        rows.append(
            [
                str(registration.id),
                registration.company_name,
                registration.contact_name,
                registration.contact_phone,
                registration.city,
                registration.attendees.count(),
                attendees,
                registration.get_project_count_display(),
                registration.get_lawsuit_count_display(),
                "；".join(registration.priority_issue_labels()),
                registration.other_risk,
                registration.get_source_channel_display(),
                timezone.localtime(registration.submitted_at).strftime("%Y-%m-%d %H:%M:%S"),
                "已发送" if registration.feishu_notified_at else registration.feishu_error,
            ]
        )
    return headers, rows


def registration_csv_response(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="event-registrations.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    headers, rows = registration_export_table(queryset)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def registration_xlsx_response(queryset):
    headers, rows = registration_export_table(queryset)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "活动报名"
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
    response["Content-Disposition"] = 'attachment; filename="event-registrations.xlsx"'
    return response


def registration_markdown_response(queryset):
    registrations = list(queryset.prefetch_related("attendees"))
    output = StringIO()
    output.write("# 活动报名记录\n\n")
    for registration in registrations:
        output.write(f"## {registration.company_name}\n\n")
        output.write(f"- 报名编号：{registration.id}\n")
        output.write(f"- 联系人：{registration.contact_name} {registration.contact_phone}\n")
        output.write(f"- 城市：{registration.city}\n")
        output.write(f"- 合作项目数量：{registration.get_project_count_display()}\n")
        output.write(f"- 涉诉/追索数量：{registration.get_lawsuit_count_display()}\n")
        output.write(f"- 了解渠道：{registration.get_source_channel_display()}\n")
        output.write("\n### 参会人员\n\n")
        for person in registration.attendees.all():
            output.write(f"- {person.name}｜{person.role}｜{person.phone}\n")
        output.write("\n### 希望重点解答的问题\n\n")
        for label in registration.priority_issue_labels():
            output.write(f"- {label}\n")
        if registration.other_risk:
            output.write(f"\n### 其他风险\n\n{registration.other_risk}\n")
        submitted_at = timezone.localtime(registration.submitted_at).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        output.write(f"\n提交时间：{submitted_at}\n\n---\n\n")
    response = HttpResponse(output.getvalue(), content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="event-registrations.md"'
    return response
